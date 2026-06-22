import os
import sys
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from twilio.rest import Client
from dotenv import load_dotenv

# ==========================================================
# CORRECCIÓN DEFINITIVA DE ENCODING PARA WINDOWS
# ==========================================================
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

# 1. Cargar configuraciones de seguridad desde el .env
load_dotenv()

# ==========================================================
# CÁLCULO DINÁMICO DE RUTA PARA EL ARCHIVO DE CREDENCIALES
# ==========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")

# 2. Probar conexión con Google Sheets API
print("🔄 Conectando con Google Sheets API...")
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    # Ahora usamos la ruta absoluta calculada dinámicamente
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
    client_sheets = gspread.authorize(creds)
    
    # Abre la hoja de cálculo por su nombre exacto
    sheet = client_sheets.open("inventario_whatsapp").sheet1
    
    # Leer datos de prueba (Fila 2, Columna 1 -> Debe ser 'Velas')
    producto = sheet.cell(2, 1).value
    stock = sheet.cell(2, 3).value
    print(f"✅ Conexión a Google Sheets exitosa. Producto encontrado: {producto} (Stock: {stock})")
except Exception as e:
    print(f"❌ Error al conectar con Google Sheets: {e}")
    producto, stock = "Error", 0

# 3. Probar envío de WhatsApp con Twilio
print("\n🔄 Probando envío de notificación a WhatsApp...")
try:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    client_twilio = Client(account_sid, auth_token)

    message = client_twilio.messages.create(
        from_='whatsapp:+14155238886', 
        body=f"📦 *Alerta de Inventario (Prueba de Sistema)*\n\nConexión exitosa con la base de datos de la PyME. El producto '{producto}' cuenta con {stock} unidades disponibles.",
        to='whatsapp:+521XXXXXXXXXX'  # Tu número
    )
    print(f"✅ Mensaje enviado con éxito por WhatsApp. SID del mensaje: {message.sid}")
except Exception as e:
    print(f"❌ Error al enviar mensaje por Twilio: {e}")