import os
import sys
import string
from datetime import datetime
from flask import Flask, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from twilio.twiml.messaging_response import MessagingResponse

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__)

# CENTRALIZACIÓN DE BASE DE DATOS (GOOGLE SHEETS API)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, SCOPE)
    client_sheets = gspread.authorize(creds)
    spreadsheet = client_sheets.open("inventario_whatsapp")
except Exception as e:
    print(f"❌ Error crítico al inicializar Google Sheets API: {e}")

# ==========================================================
# LIMPIEZA ROBUSTA DE TEXTO (Quita signos de puntuación de verdad)
# ==========================================================
def limpiar_texto(texto):
    """Normaliza las cadenas de texto del usuario removiendo puntuación y espacios."""
    if not texto:
        return ""
    texto = texto.lower().strip()
    return texto.translate(str.maketrans('', '', string.punctuation + '¿?¡!'))

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get('Body', '')
    user_number = request.values.get('From', '')          
    user_name = request.values.get('ProfileName', 'Cliente') 

    msg_limpio = limpiar_texto(incoming_msg)
    response = MessagingResponse()
    reply = ""

    try:
        sheet_inventario = spreadsheet.sheet1
        try:
            sheet_leads = spreadsheet.worksheet("leads")
        except gspread.exceptions.WorksheetNotFound:
            sheet_leads = spreadsheet.add_worksheet(title="leads", rows="100", cols="4")
            sheet_leads.append_row(["Fecha/Hora", "Nombre", "Teléfono", "Mensaje Recibido"])
    except Exception as e:
        print(f"❌ Error de comunicación con las hojas de cálculo: {e}")
        response.message("⚠️ Lo siento, nuestro sistema de datos está en mantenimiento. Intenta más tarde.")
        return str(response)

    # ==========================================================
    # FILTRO DE INTENCIONES OPTIMIZADO
    # ==========================================================
    
    # INTENCIÓN 1: Consulta de Stock
    if "stock" in msg_limpio or "tienen" in msg_limpio or "precio" in msg_limpio:
        records = sheet_inventario.get_all_records()
        encontrado = False
        
        for item in records:
            # Limpiamos también el nombre del producto por si el cliente dejó espacios en el Excel
            producto_sheet_limpio = limpiar_texto(item.get('Producto', ''))
            
            if producto_sheet_limpio and (producto_sheet_limpio in msg_limpio):
                reply = (f"📦 *Verificación de Inventario En Tiempo Real*\n\n"
                         f"El producto *{item['Producto']}* se encuentra disponible.\n"
                         f"💰 *Precio:* ${item['Precio']} MXN\n"
                         f"📉 *Disponibilidad:* {item['Stock']} unidades en almacén.\n\n"
                         f"Si deseas adquirirlo, escribe la palabra *'Cotizar'*.")
                encontrado = True
                break
                
        if not encontrado:
            reply = "🔍 No logré identificar ese producto en nuestro catálogo actual. Próximamente agregaremos más stock."

    # INTENCIÓN 2: Captura y Registro de Lead
    elif any(k in msg_limpio for k in ["cotizar", "interesa", "quiero", "comprar", "informacion", "información"]):
        fecha_registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        telefono_limpio = user_number.replace("whatsapp:", "")
        
        sheet_leads.append_row([fecha_registro, user_name, telefono_limpio, incoming_msg])
        
        reply = (f"✨ *¡Excelente decisión, {user_name}!* ✨\n\n"
                 f"Hemos registrado tu solicitud en nuestro sistema de atención a clientes.\n\n"
                 f"Un asesor de nuestro equipo se comunicará contigo al número *{telefono_limpio}* "
                 f"para completar tu orden. ¡Gracias por tu confianza! 🚀")

    # INTENCIÓN 3: Fallback Global
    else:
        reply = (f"¡Hola, {user_name}! 👋 Bienvenido al asistente automatizado de la PyME.\n\n"
                 f"Puedo ayudarte a consultar información de manera inmediata. Prueba escribiendo:\n"
                 f"• _¿Tienen stock de Velas?_\n"
                 f"• _Quiero cotizar un pedido_")

    response.message(reply)
    return str(response)

if __name__ == "__main__":
    app.run(port=5000, debug=True)