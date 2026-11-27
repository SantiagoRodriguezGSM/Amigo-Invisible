#!/usr/bin/env python3
import json
import random
import smtplib
import time
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.units import cm

# NUEVO: para soportar emojis
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# -------------------- Funciones --------------------
pdfmetrics.registerFont(TTFont("Symbola", "../ts/Symbola.ttf"))


def load_participants(path="participants.json"):
    with open(path, "r", encoding="utf-8") as f:
        participants = json.load(f)
    if len(participants) < 2:
        raise ValueError("Se necesitan al menos 2 participantes.")
    return participants


def generate_derangement(n):
    lst = list(range(n))
    while True:
        random.shuffle(lst)
        if all(i != lst[i] for i in range(n)):
            return lst


def create_christmas_pdf(name, assigned_to, output_path):
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    # --- Fondo navideño ---
    c.setFillColor(HexColor("#F7F2E9"))
    c.rect(0, 0, width, height, fill=1)

    # --- Marco decorativo ---
    c.setStrokeColor(HexColor("#B30000"))
    c.setLineWidth(8)
    margin = 25
    c.rect(margin, margin, width - 2*margin, height - 2*margin, fill=0)

    # --- Título ---
    c.setFont("Symbola", 28)
    c.setFillColor(HexColor("#B30000"))
    c.drawCentredString(width/2, height - 4*cm, "🎄 ¡Tu Amigo Invisible! 🎁")

    # --- Mensaje ---
    c.setFont("Symbola", 16)
    c.setFillColor(HexColor("#333333"))

    text = c.beginText()
    text.setTextOrigin(3*cm, height - 7*cm)
    text.setLeading(28)
    text.textLine(f"Hola {name},")
    text.textLine("")
    text.textLine("Te ha tocado hacer un regalo para:")
    text.setFont("Symbola", 22)
    text.textLine(f"🎁 {assigned_to} 🎁")
    text.setFont("Symbola", 16)
    text.textLine("")
    text.textLine("El presupuesto para el regalo es de 20€ a 30€ 🎅🎄")
    text.textLine("")
    text.textLine("¡El amigo invisible tendra lugar en nochebuena! 🌟")
    c.drawText(text)

    # --- Pie ---
    c.setFont("Symbola", 12)
    c.setFillColor(HexColor("#666666"))
    c.drawCentredString(width/2, 1.5*cm, "Feliz Navidad y felices fiestas ❄️🎁")

    c.save()


def send_email(sender_email, sender_password, receiver_email, subject, attachment_path):
    msg = EmailMessage()

    # Cabeceras importantes
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg["Reply-To"] = sender_email
    msg["Return-Path"] = sender_email

    # Identificador único (muy recomendado)
    msg["Message-ID"] = make_msgid()
    msg["MIME-Version"] = "1.0"
    msg["X-Mailer"] = "Python SMTP"

    # Versión en texto plano
    msg.set_content(
        "Hola!\n\n"
        "Ya tienes disponible tu archivo PDF con el nombre de la persona a la que te ha tocado hacer el regalo del amigo invisible\n"
        "Abre el archivo adjunto para ver a quién te ha tocado.\n\n"
        "¡Felices fiestas!\n"
        "El presupuesto es de 20€ a 30€\n"
        "¡Que tengas unas muy felices fiestas!\n"
        "\n Este mensaje ha sido enviado automáticamente por el organizador del Amigo Invisible."
        
    )

    # Versión HTML segura (bonita pero ligera)
    html_body = """
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #fafafa; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #e5e5e5;">
            
            <h2 style="text-align: center; color: #b30000; margin-bottom: 10px; font-size: 22px;">
                Información de tu Amigo Invisible
            </h2>

            <p style="font-size: 15px; color: #333333; line-height: 1.5;">
                Hola,<br><br>
                Ya tienes disponible tu archivo PDF con el nombre de la persona a la que te ha tocado hacer el regalo del amigo invisible. 
                Puedes encontrarlo adjunto a este correo.
            </p>

            <p style="font-size: 15px; color: #333333; line-height: 1.5;">
                El presupuesto es de <strong>20€ a 30€</strong>.
            </p>

            <div style="margin: 20px 0; padding: 10px; background: #f7f2ed; border-left: 4px solid #b30000;">
                <p style="margin: 0; font-size: 14px; color: #444;">
                    🎄 La entrega del amigo invisible tendrá lugar en Nochebuena.  
                </p>
            </div>

            <p style="font-size: 14px; color: #555; line-height: 1.5; text-align:center;">
                ¡Que tengas unas muy felices fiestas!
            </p>
        </div>

        <p style="text-align:center; font-size: 12px; color: #999; margin-top: 20px;">
            Este mensaje ha sido enviado automáticamente por el organizador del Amigo Invisible.
        </p>
    </body>
    </html>
    """

    msg.add_alternative(html_body, subtype="html")

    # Adjuntar PDF
    with open(attachment_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename=Path(attachment_path).name
        )

    # Envío usando SMTP cifrado
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender_email, sender_password)
        smtp.send_message(msg)



def main():
    participants = load_participants()
    names = [p["name"] for p in participants]

    perm = generate_derangement(len(participants))

    Path("../pdfs").mkdir(exist_ok=True)

    print("\n=== ENVÍO NAVIDEÑO DE AMIGO INVISIBLE 🎄 ===\n")

    sender = ""
    password = ""

    for i, p in enumerate(participants):
        assigned = participants[perm[i]]["name"]

        pdf_path = f"../pdfs/{p['name'].replace(' ', '_')}.pdf"
        create_christmas_pdf(p["name"], assigned, pdf_path)

        send_email(
            sender,
            password,
            p["email"],
            "Asigna​ción de tu amigo invisible",
            pdf_path
        )

        print(f"✔ Enviado a {p['email']}")
        time.sleep(5)
    print("\n🎅✨ ¡Todos los PDF navideños han sido enviados! ✨🎅\n")


if __name__ == "__main__":
    main()