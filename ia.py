"""Cliente Chat Completions compatible y tratamiento prudente del JSON devuelto."""
from __future__ import annotations
import base64
import os
import json
import re
import hashlib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import database
import storage_config

_SESSION_KEY = None
_PORTABLE_CIPHER_KEY = None


def secret_file():
    """Nunca en SQLite ni junto al EXE; siempre en la carpeta de datos elegida."""
    return database.DATA / 'seguridad' / 'api_cifrada.json'


def secret_saved():
    if storage_config.PORTABLE:
        return secret_file().is_file()
    if _SESSION_KEY:
        return True
    try:
        import keyring
        return bool(keyring.get_password('EvaluaFPCanarias', 'api_key'))
    except Exception:
        return False


def secret_status():
    return {'api_key_saved':secret_saved(), 'api_key_unlocked':key_available(),
            'api_key_persistent':secret_saved(), 'portable':storage_config.PORTABLE}


def _cipher(password, salt):
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    kdf=Scrypt(salt=salt,length=32,n=2**14,r=8,p=1)
    return kdf.derive(password.encode('utf-8'))


def unlock_secret(password):
    """Desbloqueo explícito al iniciar en otro PC; nunca persiste la contraseña."""
    global _SESSION_KEY, _PORTABLE_CIPHER_KEY
    if not storage_config.PORTABLE:
        return key_available()
    if not password:
        raise ValueError('Introduzca la contraseña maestra del pendrive.')
    path=secret_file()
    if not path.exists():
        raise ValueError('No hay ninguna clave API cifrada guardada todavía.')
    try:
        payload=json.loads(path.read_text(encoding='utf-8'))
        salt=base64.b64decode(payload['salt'], validate=True)
        nonce=base64.b64decode(payload['nonce'], validate=True)
        sealed=base64.b64decode(payload['ciphertext'],validate=True)
        if payload.get('version') != 1 or len(salt)!=16 or len(nonce)!=12:
            raise ValueError('Formato de la clave cifrada incorrecto.')
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        key=_cipher(password,salt)
        secret=AESGCM(key).decrypt(nonce,sealed,b'EvaluaFPCanarias portable API v1').decode('utf-8')
    except Exception as exc:
        _SESSION_KEY=None;_PORTABLE_CIPHER_KEY=None
        raise ValueError('Contraseña incorrecta o archivo de clave cifrada dañado.') from exc
    _SESSION_KEY=secret
    _PORTABLE_CIPHER_KEY=key
    return True


def lock_secret():
    global _SESSION_KEY, _PORTABLE_CIPHER_KEY
    _SESSION_KEY=None
    _PORTABLE_CIPHER_KEY=None


def set_secret(secret, password=None):
    global _SESSION_KEY, _PORTABLE_CIPHER_KEY
    if secret is None:
        return key_available(), secret_saved()
    secret=str(secret).strip()
    if storage_config.PORTABLE:
        if not secret:
            secret_file().unlink(missing_ok=True)
            lock_secret()
            return False, True
        if password is None or len(str(password)) < 12:
            raise ValueError('Para guardar la API en el USB, establezca una contraseña maestra de al menos 12 caracteres.')
        salt=os.urandom(16);nonce=os.urandom(12)
        key=_cipher(str(password),salt)
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        enc=AESGCM(key).encrypt(nonce,secret.encode('utf-8'),b'EvaluaFPCanarias portable API v1')
        path=secret_file();path.parent.mkdir(parents=True,exist_ok=True)
        payload={'version':1,'algorithm':'AES-256-GCM','kdf':'scrypt',
                 'salt':base64.b64encode(salt).decode('ascii'),
                 'nonce':base64.b64encode(nonce).decode('ascii'),
                 'ciphertext':base64.b64encode(enc).decode('ascii')}
        tmp=path.with_suffix('.tmp')
        tmp.write_text(json.dumps(payload,indent=2),encoding='utf-8')
        tmp.replace(path)
        try:os.chmod(path,0o600)
        except OSError:pass
        _SESSION_KEY=secret
        _PORTABLE_CIPHER_KEY=key
        return True, True
    _SESSION_KEY=secret or None
    if not secret:
        try:
            import keyring
            keyring.delete_password('EvaluaFPCanarias','api_key')
        except Exception:pass
        return False,True
    try:
        import keyring
        keyring.set_password('EvaluaFPCanarias','api_key',secret)
        return True,True
    except Exception:
        return True,False


def get_secret():
    if storage_config.PORTABLE:
        return _SESSION_KEY  # Nunca recurrir a la credencial de otro ordenador.
    if _SESSION_KEY:
        return _SESSION_KEY
    try:
        import keyring
        return keyring.get_password('EvaluaFPCanarias', 'api_key')
    except Exception:
        return None


def key_available():
    return bool(get_secret())


def settings():
    with database.connect() as d:
        return database.pref(d, 'ai', {
            'provider': 'OpenAI', 'base_url':'https://api.openai.com/v1',
            'model_generation':'gpt-4o', 'model_vision':'gpt-4o',
            'model_correction':'gpt-4o', 'model_analysis':'gpt-4o'
        })


def check_url(url):
    u = urllib.parse.urlparse(url)
    if not (u.scheme == 'https' or (u.scheme == 'http' and u.hostname in {'localhost','127.0.0.1','::1'})):
        raise ValueError('La API debe usar HTTPS, o HTTP solo para proveedores locales (localhost).')
    if not u.hostname or u.username or u.password or u.query or u.fragment:
        raise ValueError('URL de API no válida')
    return url.rstrip('/')


def chat(role, prompt, images=None, limit=16000):
    conf = settings()
    model = conf['model_' + role]
    url = check_url(conf['base_url'])
    key = get_secret()
    if not key and not urllib.parse.urlparse(url).hostname in {'localhost','127.0.0.1','::1'}:
        raise ValueError('Configure primero la clave API en Ajustes.')
    content = [{'type':'text','text':prompt}]
    for p in images or []:
        blob = Path(p).read_bytes()
        content.append({'type':'image_url','image_url':{
            'url':'data:image/jpeg;base64,' + base64.b64encode(blob).decode('ascii'), 'detail':'high'}})
    payload = {'model': model, 'messages': [
        {'role':'system','content':'Eres un asistente experto en evaluación de Formación Profesional en España. Sigue los criterios de evaluación dados. Responde exclusivamente JSON válido sin Markdown. No inventes información que no esté en el material.'},
        {'role':'user','content':content if images else prompt}
    ], 'response_format':{'type':'json_object'}}
    endpoint = url + ('/chat/completions' if not url.endswith('/chat/completions') else '')
    for retry in range(2):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(endpoint, body, headers={
            'Content-Type':'application/json', 'Authorization':'Bearer '+(key or 'local')}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=210) as r:
                response = json.loads(r.read().decode('utf-8'))
            raw = response['choices'][0]['message']['content']
            if isinstance(raw, list):
                raw = ''.join(p.get('text','') for p in raw if isinstance(p,dict))
            result = clean_json(raw)
            return result, model
        except urllib.error.HTTPError as ex:
            detail = ex.read(1200).decode('utf-8', 'replace')
            if ex.code in (400,422) and retry == 0 and 'response_format' in payload:
                del payload['response_format']
                continue
            raise ValueError(f'API HTTP {ex.code}: {detail}')
        except (urllib.error.URLError, TimeoutError) as ex:
            raise ValueError(f'No se ha podido contactar con la API: {ex}')
    raise ValueError('La API no ha devuelto un JSON utilizable.')


def clean_json(raw):
    raw = str(raw or '').strip()
    if raw.startswith('```'):
        raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw, flags=re.IGNORECASE)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        first = raw.find('{'); last = raw.rfind('}')
        if first >= 0 and last > first:
            return json.loads(raw[first:last+1])
        raise ValueError('El modelo devolvió una respuesta que no es JSON válido. No se ha almacenado ninguna calificación.')
