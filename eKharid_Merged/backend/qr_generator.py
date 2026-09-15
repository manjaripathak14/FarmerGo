import qrcode
import io
import base64

def generate_gate_pass_qr(gate_pass_id: str) -> str:
    """Generates Base64 encoded PNG string of QR Code."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(gate_pass_id)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    
    return f"data:image/png;base64,{img_str}"

generate_qr_base64 = generate_gate_pass_qr