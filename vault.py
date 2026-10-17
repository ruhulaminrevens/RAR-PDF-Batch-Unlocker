"""Optional Windows OS credential store. Requires `keyring` and a secure Windows backend."""
import sys
SERVICE = 'RAR PDF Batch Unlocker'

def _store():
    if sys.platform != 'win32':
        raise RuntimeError('Optional vault is supported only on Windows.')
    try:
        import keyring
        from keyring.backends.Windows import WinVaultKeyring
    except ImportError as exc:
        raise RuntimeError('Install the optional dependency: py -3 -m pip install keyring') from exc
    kr = keyring.get_keyring()
    if not isinstance(kr, WinVaultKeyring):
        raise RuntimeError('Windows Credential Locker backend is not active. No password was stored.')
    return kr

def save(name, password):
    if not name.strip() or not password or any(c in name for c in '\r\n'):
        raise ValueError('Vault entry name and password are required.')
    _store().set_password(SERVICE, name, password)

def load(name):
    return _store().get_password(SERVICE, name)

def delete(name):
    return _store().delete_password(SERVICE, name)
