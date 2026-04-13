from authlib.integrations.starlette_client import OAuth
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
from db import query, execute

oauth = OAuth()
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

def upsert_cliente(google_id: str, email: str, nombre: str, foto_url: str) -> dict:
    cliente = query(
        'SELECT * FROM clientes WHERE google_id=%s', (google_id,), many=False
    )
    if cliente:
        execute(
            'UPDATE clientes SET email=%s, nombre=%s, foto_url=%s, ultimo_login=NOW() WHERE google_id=%s',
            (email, nombre, foto_url, google_id)
        )
        return query('SELECT * FROM clientes WHERE google_id=%s', (google_id,), many=False)
    else:
        return execute(
            'INSERT INTO clientes (google_id, email, nombre, foto_url) VALUES (%s,%s,%s,%s) RETURNING *',
            (google_id, email, nombre, foto_url), returning=True
        )

def get_cliente_session(request) -> dict | None:
    return request.session.get('cliente')
