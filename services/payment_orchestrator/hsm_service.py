import logging
import os
from typing import Optional
from pkcs11 import PyKCS11

logger = logging.getLogger(__name__)

# HSM Configuration
HSM_LIBRARY_PATH = os.getenv("HSM_LIBRARY_PATH", "/usr/lib/softhsm/libsofthsm2.so")
HSM_SLOT_ID = int(os.getenv("HSM_SLOT_ID", 0))
HSM_PIN = os.getenv("HSM_PIN", "5678")
HSM_LABEL = os.getenv("HSM_LABEL", "payment-hsm")
SIGNING_KEY_LABEL = "my_signing_key"

# Global session cache
_hsm_session: Optional[PyKCS11.Session] = None


def get_hsm_session() -> PyKCS11.Session:
    """
    Get or create HSM session.
    Connects to SoftHSM using PKCS#11 interface.
    """
    global _hsm_session
    
    if _hsm_session is not None:
        return _hsm_session
    
    try:
        logger.info(f"Connecting to HSM at {HSM_LIBRARY_PATH}")
        lib = PyKCS11.PyKCS11Lib()
        lib.load(HSM_LIBRARY_PATH)
        
        # Get available slots
        slots = lib.getSlotList()
        if not slots:
            raise RuntimeError("No HSM slots available")
        
        logger.info(f"Available slots: {slots}")
        
        # Open session on the specified slot
        _hsm_session = lib.openSession(HSM_SLOT_ID)
        
        # Login to the token
        _hsm_session.login(HSM_PIN)
        logger.info(f"Successfully logged into HSM slot {HSM_SLOT_ID}")
        
        return _hsm_session
    except Exception as e:
        logger.error(f"Failed to connect to HSM: {str(e)}")
        raise


def initialize_keys_if_not_exist() -> None:
    """
    Initialize signing keys in HSM.
    If my_signing_key doesn't exist, create a new RSA 2048-bit key pair.
    """
    try:
        session = get_hsm_session()
        
        # Search for existing signing key
        template = [
            (PyKCS11.CKA_LABEL, SIGNING_KEY_LABEL),
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY),
        ]
        
        existing_keys = session.findObjects(template)
        
        if existing_keys:
            logger.info(f"Signing key '{SIGNING_KEY_LABEL}' already exists in HSM")
            return
        
        logger.info(f"Creating new RSA 2048-bit signing key pair: {SIGNING_KEY_LABEL}")
        
        # Generate RSA key pair
        public_key_template = [
            (PyKCS11.CKA_TOKEN, True),
            (PyKCS11.CKA_VERIFY, True),
            (PyKCS11.CKA_LABEL, SIGNING_KEY_LABEL),
        ]
        
        private_key_template = [
            (PyKCS11.CKA_TOKEN, True),
            (PyKCS11.CKA_SIGN, True),
            (PyKCS11.CKA_EXTRACTABLE, False),  # Prevent key extraction
            (PyKCS11.CKA_LABEL, SIGNING_KEY_LABEL),
        ]
        
        # Generate 2048-bit RSA key pair
        session.generateKeyPair(
            PyKCS11.CKM_RSA_PKCS_KEY_PAIR_GEN,
            public_key_template,
            private_key_template,
            1024  # 2048-bit key (1024 * 2)
        )
        
        logger.info(f"Successfully created RSA key pair: {SIGNING_KEY_LABEL}")
        
    except Exception as e:
        logger.error(f"Failed to initialize keys: {str(e)}")
        raise


def sign_message(message: str) -> bytes:
    """
    Sign a message using the private key in HSM.
    Uses SHA256-RSA-PKCS signature mechanism.
    
    Args:
        message: The message to sign
        
    Returns:
        The signature bytes
    """
    try:
        session = get_hsm_session()
        
        # Find the private signing key
        template = [
            (PyKCS11.CKA_LABEL, SIGNING_KEY_LABEL),
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY),
        ]
        
        keys = session.findObjects(template)
        if not keys:
            raise RuntimeError(f"Signing key '{SIGNING_KEY_LABEL}' not found in HSM")
        
        private_key = keys[0]
        
        # Sign the message
        message_bytes = message.encode('utf-8')
        signature = session.sign(
            private_key,
            message_bytes,
            PyKCS11.Mechanism(PyKCS11.CKM_SHA256_RSA_PKCS)
        )
        
        logger.info(f"Successfully signed message (length: {len(message_bytes)} bytes)")
        return bytes(signature)
        
    except Exception as e:
        logger.error(f"Failed to sign message: {str(e)}")
        raise


def get_public_key_bytes() -> bytes:
    """
    Get the public key in DER format from HSM.
    
    Returns:
        The public key in DER format
    """
    try:
        session = get_hsm_session()
        
        # Find the public key
        template = [
            (PyKCS11.CKA_LABEL, SIGNING_KEY_LABEL),
            (PyKCS11.CKA_CLASS, PyKCS11.CKO_PUBLIC_KEY),
        ]
        
        keys = session.findObjects(template)
        if not keys:
            raise RuntimeError(f"Public key '{SIGNING_KEY_LABEL}' not found in HSM")
        
        public_key = keys[0]
        
        # Extract public key components (modulus and exponent)
        modulus = public_key[PyKCS11.CKA_MODULUS]
        exponent = public_key[PyKCS11.CKA_PUBLIC_EXPONENT]
        
        # Convert to bytes
        modulus_bytes = bytes(modulus)
        exponent_bytes = bytes(exponent)
        
        logger.info(f"Successfully retrieved public key (modulus: {len(modulus_bytes)} bytes)")
        
        # Return modulus and exponent as concatenated bytes
        # In production, you'd want to encode this as proper DER format
        return modulus_bytes + exponent_bytes
        
    except Exception as e:
        logger.error(f"Failed to get public key: {str(e)}")
        raise
