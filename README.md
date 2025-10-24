# Secure payment gateway prototype
A project me and my bro preparing for learning and working on.

Một dự án môn học nhằm mục đích tìm hiểu, xây dựng và thử nghiệm một mô hình cổng thanh toán an toàn.

## 🎯 Mục tiêu dự án

Dự án này tập trung vào hai mục tiêu chính:

1.  **Học tập (Learning):** Nghiên cứu các thành phần cốt lõi của một hệ thống thanh toán, bao gồm xử lý giao dịch, API, và các phương pháp bảo mật.
2.  **Thực hành (Working On):** Áp dụng kiến thức về phát triển web và an ninh mạng để xây dựng một prototype có khả năng chống chịu lại các cuộc tấn công phổ biến.

## 🛡️ Trọng tâm bảo mật (Security Focus)

Vì đây là một cổng thanh toán, bảo mật là ưu tiên hàng đầu. Dự án sẽ tập trung nghiên cứu và triển khai các biện pháp phòng thủ chống lại:

* **Lỗ hổng Web phổ biến:**
    * SQL Injection (SQLi)
    * Cross-Site Scripting (XSS)
    * Server-Side Request Forgery (SSRF)
    * Cross-Site Request Forgery (CSRF)
* **Xác thực & Ủy quyền:**
    * Triển khai xác thực an toàn (ví dụ: sử dụng JWT và các cơ chế chống tấn công như JWT Algorithm Confusion).
    * Phân quyền người dùng (ví dụ: admin, user, merchant) một cách chặt chẽ.
* **Mật mã & Bảo vệ dữ liệu:**
    * Mã hóa dữ liệu nhạy cảm (như thông tin thẻ) khi lưu trữ (at-rest) và truyền tải (in-transit), có thể sử dụng các thư viện như `CryptoPP` (C++) hoặc các thư viện tương đương trong Node.js/Python.
* **Lỗ hổng Logic nghiệp vụ (Business Logic):**
    * Đảm bảo logic xử lý thanh toán (ví dụ: kiểm tra số dư, xác nhận giao dịch) được xác thực kỹ lưỡng ở phía backend, tránh các lỗ hổng do tin tưởng dữ liệu từ client.

## 💻 Công nghệ dự kiến (Potential Tech Stack)

Đây là các công nghệ dự kiến dựa trên các lĩnh vực bạn đang quan tâm:

* **Backend:** Node.js (Express) hoặc Python (FastAPI / Flask)
* **Database:** PostgreSQL / MySQL
* **Frontend (Nếu có):** Next.js / React
* **Triển khai (Deployment):** Docker & Kubernetes (Minikube)

## 🚀 Các bước tiếp theo (Roadmap)

- [ ] Thiết kế kiến trúc hệ thống (System Design)
- [ ] Định nghĩa API (API Specification)
- [ ] Xây dựng tính năng xác thực người dùng
- [ ] Xây dựng lõi xử lý giao dịch
- [ ] Viết kịch bản kiểm thử (test cases) và "pentest" (thử nghiệm xâm nhập) các tính năng đã xây dựng.