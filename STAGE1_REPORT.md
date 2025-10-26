# Stage Report – Stage 1 Progress & Security Review

## 1. Bối cảnh & mục tiêu
- **Phạm vi học thuật**: tài liệu `20_Secure Commercial Transactions and Payment Gateway (1).md` mô tả các yêu cầu về tokenization, HSM/KMS, TLS/mTLS, request signing, chống gian lận, non-repudiation và tuân thủ PCI-DSS/PSD2.
- **Kết quả mong đợi Stage 1**:
  - **Hạ tầng**: dựng stack Docker Compose với Postgres, RabbitMQ, SoftHSM, Keycloak, Envoy và các dịch vụ backend (order, payment orchestrator, fraud, reconciliation); frontend React hiện chỉ đóng vai trò stub cho giai đoạn sau. Trạng thái vận hành được xác nhận qua `make health` hoặc `docker-compose ps`.
  - **Chứng thực & bảo mật**: Keycloak realm sẵn sàng, Envoy kiểm tra JWT thành công/thất bại, SoftHSM được khởi tạo với khóa ký/đối xứng hoạt động.
  - **Luồng giao dịch end-to-end**: tạo order, token hóa thẻ qua HSM, xử lý thanh toán với fraud check, sinh biên lai ký số, đẩy thông điệp reconciliation; toàn bộ chuỗi được tự động hóa bằng `make test`.
  - **Quan sát & lưu trữ**: log dịch vụ đầy đủ, bảng Postgres ghi nhận payment intent và token hash, hàng đợi RabbitMQ nhận biên lai, chuẩn bị dữ liệu cho báo cáo/đối soát.

## 2. Điểm mạnh
- Kiến trúc microservices hoàn chỉnh: Envoy + Keycloak ở lớp biên; các dịch vụ FastAPI (payment orchestrator, order, fraud, reconciliation) kết nối PostgreSQL, RabbitMQ và SoftHSM theo đúng định hướng trong đề tài.
- `make test` chạy thành công, chứng minh quy trình order → tokenization HSM → gọi PSP mock → ký biên lai → gửi RabbitMQ hoạt động trọn vẹn.
- SoftHSM tự khởi tạo và quản lý khóa RSA/AES qua PKCS#11; biên lai ký số và token hash được lưu trữ trong Postgres để phục vụ truy xuất và kiểm toán.
- Cơ chế chống replay qua bảng `used_payment_tokens` và tích hợp fraud engine trong luồng xử lý thanh toán; reconciliation worker ghi nhận biên lai từ hàng đợi.

## 3. Lỗ hổng / Chưa đáp ứng yêu cầu bảo mật
1. **Thiếu TLS/mTLS & request signing nội bộ**  
   - Envoy và backend chỉ lộ HTTP thường (`gateway/envoy.yaml:9`, `services/payment_orchestrator/main.py:197`), không có mTLS & HMAC như yêu cầu.
   - Các dịch vụ (order/fraud) nhận `x-user-id` tin tưởng tuyệt đối mà không xác thực nguồn (`services/order/main.py:21`, `services/fraud_engine/main.py:44`).

2. **HSM & bí mật cấu hình yếu**  
   - SoftHSM khởi tạo với PIN cố định `1234/5678` (`services/softhsm/init_softhsm.sh:10`), dễ dò rỉ.  
   - Biến môi trường trong Compose lưu mật khẩu mặc định (`docker-compose.yml:9`, `docker-compose.yml:25`) trái với yêu cầu runbook bảo mật.

3. **Tokenization thiếu tính toàn vẹn**  
   - Token `hsm:v1` chỉ dùng AES-CBC không kèm MAC (`services/payment_orchestrator/hsm_service.py:166`), kẻ tấn công có thể sửa đổi ciphertext.  
   - Log còn ghi prefix token (`services/payment_orchestrator/main.py:148`), tăng rủi ro lộ dữ liệu nhạy cảm.

4. **Thiếu ràng buộc token/thiết bị & PCI scope**  
   - Order Service vẫn lưu `payment_token` và trả về nguyên trạng (`services/order/main.py:41`), không giảm phạm vi PCI như tài liệu yêu cầu hosted fields/token binding.  
   - Không có nonce hoặc device binding kiểm chứng token thuộc phiên nào.

5. **Reconciliation chưa thực hiện xác minh non-repudiation**  
   - Worker lưu receipt mà không xác thực chữ ký (`services/reconciliation/main.py:27`), mâu thuẫn mục tiêu non-repudiation ở tài liệu.

6. **SCA/3DS và fraud đa lớp chưa hiện diện**  
   - Fraud Engine mới có rule theo số tiền (`services/fraud_engine/main.py:44`), thiếu ML/device binding/3DS như mục tiêu (`20_Secure Commercial Transactions...` mục 5 & 16).  

## 4. Hành động cải thiện ưu tiên
1. **Bảo mật đường truyền nội bộ**  
   - Bật TLS/mTLS giữa Envoy và backend, chuyển `ORDER_SERVICE_URL`/`FRAUD_ENGINE_URL` sang HTTPS và bổ sung HMAC hoặc JWS cho payload nội bộ.
2. **Quản lý bí mật & HSM**  
   - Thay PIN SoftHSM bằng cấu hình bí mật từ secret manager; loại bỏ mật khẩu mặc định khỏi repository; xây dựng quy trình rotation theo tài liệu.
3. **Token hóa an toàn**  
   - Chuyển sang AES-GCM hoặc AES-CBC + HMAC; xóa log token; xem xét ký token với metadata ràng buộc đơn hàng/thiết bị.
4. **Giảm PCI scope**  
   - Order service chỉ giữ token tham chiếu (không trả về), hoặc lưu trữ trong hệ thống vault/HSM; triển khai hosted fields / client-side tokenization thực sự ở frontend.
5. **Xác thực biên lai & quan sát**  
   - Reconciliation worker cần verify signature trước khi lưu; lưu kết quả và cảnh báo khi sai chữ ký.
6. **Mở rộng chống gian lận & SCA**  
   - Bổ sung rule hành vi, device fingerprint, velocity, 3DS fallback; ghi lại metric để phù hợp mục tiêu mục 5/11 của tài liệu.
7. **Tự động hóa kiểm thử Stage 1**  
   - Lưu lại kết quả `make test` (log hoặc artefact) và tiếp tục bổ sung kiểm thử cho các trường hợp thất bại/tấn công nhằm đáp ứng checklist và tài liệu yêu cầu.

## 5. Ghi chú & đề xuất tiếp theo
- Khi hoàn thiện từng hạng mục, nên cập nhật `STAGE1_CHECKLIST.md` với trạng thái thực tế và lưu kèm log/ghi chú thao tác để làm minh chứng.  
- Xây dựng bảng đối chiếu PCI-DSS/PSD2 trong thư mục docs nhằm chuẩn bị cho Stage 2 theo yêu cầu phần 13 của tài liệu chính.  
- Sau khi triển khai cải tiến, nên thực hiện pentest mô phỏng replay/token tampering để đo lường tiến bộ so với các chỉ số trong mục 11 của tài liệu chính.

## 6. Tổng quan kiến trúc & tiến độ Stage 1 (dành cho báo cáo)
- **Kiến trúc tổng quát**: Envoy làm cổng API (JWT + RBAC) đứng trước các dịch vụ FastAPI; Keycloak realm `ecommerce` phát hành token; SoftHSM quản lý cặp khóa RSA/AES thông qua PKCS#11; RabbitMQ xử lý hàng đợi biên lai; PostgreSQL lưu trữ đơn hàng, intent và dấu vết chống replay; frontend React là stub cho bước tích hợp hosted fields và 3-D Secure.
- **Hạng mục đã hoàn thành**:
  - `make test` chạy thành công, chứng minh luồng order → tokenization HSM → charge PSP mock → ký biên lai → đẩy RabbitMQ hoạt động trọn vẹn.
  - SoftHSM tự khởi tạo và sinh khóa khi dịch vụ payment orchestrator start; receipt và token hash được lưu vào Postgres.
  - Fraud engine được gọi trong quá trình xử lý thanh toán và reconciliation worker ghi nhận biên lai từ RabbitMQ.
- **Hạng mục còn thiếu / rủi ro**:
  - Lưu lượng nội bộ vẫn dùng HTTP, chưa có mTLS hay request signing; tin cậy `x-user-id` từ Envoy mà không xác thực bổ sung.
  - PIN SoftHSM và mật khẩu cơ sở dữ liệu dùng giá trị cố định; chưa có cơ chế xoay vòng hoặc quản lý bí mật tập trung.
  - Định dạng token AES-CBC thiếu MAC và Order Service vẫn lưu/trả token thô, chưa giảm phạm vi PCI như mục tiêu.
  - Reconciliation worker chưa verify chữ ký biên lai; Fraud/SCA chỉ mới có rule theo số tiền, chưa có 3DS hay device binding.
- **Lệnh mẫu & kết quả mong đợi**:
  ```bash
   m321@LaptopOfMinhHandsome:~/doAn/mmh/NT219_aPlatformForTransactionProtectedByCrypto$ make health     # các dịch vụ backend và hạ tầng báo trạng thái ok
   make test       # kết thúc với thông điệp “All integration tests PASSED”

   TOKEN=$(make -s token)
   ORDER_ID=$(curl -s -X POST http://localhost:8001/orders \
      -H "x-user-id: customer1" -H "Content-Type: application/json" \
      -d '{"amount":200000,"currency":"VND","items":[]}' | jq -r '.id')
   PAYMENT_TOKEN=$(curl -s -X POST http://localhost:10000/api/payment/tokenize \
      -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
      -d '{"pan":"4111111111111111","exp_month":12,"exp_year":2030,"cvc":"123"}' | jq -r '.token')
   curl -s -X POST http://localhost:10000/api/payments \
      -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
      -d "{\"order_id\":\"$ORDER_ID\",\"payment_token\":\"$PAYMENT_TOKEN\"}"
   Checking service health...
   ok
   ✓ Envoy
   {"status":"ok","service":"order"}✓ Order Service
   {"status":"ok","provider":"mock"}✓ Payment Orchestrator
   {"status":"ok"}✓ Fraud Engine
   ✓ Keycloak
   /var/run/postgresql:5432 - accepting connections
   ✓ PostgreSQL
   Will ping rabbit@16d0b0f99937. This only checks if the OS process is running and registered with epmd. Timeout: 60000 ms.
   Ping succeeded
   ✓ RabbitMQ
   Available slots:
   ✓ SoftHSM
   docker-compose up -d --remove-orphans
   WARN[0000] The "STRIPE_PUBLISHABLE_KEY" variable is not set. Defaulting to a blank string. 
   WARN[0000] The "STRIPE_SECRET_KEY" variable is not set. Defaulting to a blank string. 
   WARN[0000] The "STRIPE_WEBHOOK_SECRET" variable is not set. Defaulting to a blank string. 
   WARN[0000] /home/m321/doAn/mmh/NT219_aPlatformForTransactionProtectedByCrypto/docker-compose.yml: the attribute `version` is obsolete, it will be ignored, please remove it to avoid potential confusion 
   [+] Running 10/10
   ✔ Container payment_gateway_mq              Healthy                                           0.5s 
   ✔ Container payment_gateway_hsm             Healthy                                           0.5s 
   ✔ Container payment_gateway_keycloak        Running                                           0.0s 
   ✔ Container payment_gateway_db              Healthy                                           0.5s 
   ✔ Container payment_gateway_reconciliation  Run...                                            0.0s 
   ✔ Container payment_gateway_orchestrator    Runni...                                          0.0s 
   ✔ Container payment_gateway_order           Running                                           0.0s 
   ✔ Container payment_gateway_envoy           Running                                           0.0s 
   ✔ Container payment_gateway_fraud           Running                                           0.0s 
   ✔ Container payment_gateway_frontend        Running                                           0.0s 
   ./scripts/integration_test.sh
   [TEST] Obtaining JWT token from Keycloak...
   [PASS] JWT token obtained
   [TEST] Checking Envoy gateway health...
   [PASS] Envoy gateway is healthy
   [TEST] Checking Payment Orchestrator health...
   [PASS] Payment Orchestrator is healthy
   [TEST] Creating order...
   [PASS] Order created: 1a2613fd-480f-4db4-91f0-4a96eaa933b7
   [TEST] Tokenizing card via HSM...
   [PASS] Card tokenized: hsm:v1:wp_HTHAzbWHa05yrWxO6gcP...
   [TEST] Processing payment with fraud check...
   [PASS] Payment processed successfully
   [TEST] Verifying signed receipt...
   [PASS] Signed receipt obtained: hZ4BiGLEsLhSAcflF3zMmS/81UnhuW...
   [TEST] Waiting for reconciliation worker to process receipt (up to 20s)...
   [PASS] Reconciliation entry confirmed in database
   [TEST] Dumping HSM information...
   Available slots:
   Slot 1916774973
      Slot info:
         Description:      SoftHSM slot ID 0x723faa3d                                      
         Manufacturer ID:  SoftHSM project                 

   ========================================
   All integration tests PASSED
   ========================================

   Summary:
   - Order ID: 1a2613fd-480f-4db4-91f0-4a96eaa933b7
   - Payment Token: hsm:v1:wp_HTHAzbWHa05yrWxO6gcP...
   - Signed Receipt: hZ4BiGLEsLhSAcflF3zMmS/81UnhuW...
   - Reconciliation Records: 1
   {"status":"SUCCESS","signed_receipt":"clA5pqTV8i9Wpn4vgg7U9474zSYP7R6B5tdiUn91vaVV2Vy6vqkYARW6RVDlXpv1eUbIInc2mz56Jf66oaU6N3LOUNGEY8K8nJf0GefQASdKZJUi7eXKR8E4nkKyiFPImNt2waEI+HmRq8wDZ+okH5OIHUH72+Lz540HtuDgxoQKKQmA1chg3uwjq6vZr18LjNMaqA1RqqOaly7Q+wiTZiIW8exuQwy8/7QLgwXeo+8dADJ5jQrILGl7kCWaG6zdTHE8AALV/+ub8WyasePULGMQ2yCt8nkqG8bGCJuB1Ko25YQ0S9v63DkKjjSJuGn5+7VyjcGzbObDNFVmMWI77A==","receipt":{"order_id":"390183cc-3789-44b2-b3f6-e6db1bd6abb1","amount":200000,"currency":"VND","timestamp":"2025-10-26T13:29:29.917652+00:00","status":"SUCCESS","provider":"mock","psp_reference":"pi_mock_732c224553a3469e","last4":"1111"}}
  # => trả về JSON chứa status SUCCESS, signed_receipt và payload biên lai
  ```
