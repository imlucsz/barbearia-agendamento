"""Small paginated text PDF, using the standard PDF Helvetica font."""
import textwrap


def personal_data_pdf(data):
    user = data["usuario"]
    lines = ["Meus dados", f"Nome: {user['nome']}", f"E-mail: {user['email']}", "", "Agendamentos"]
    for item in data["agendamentos"]:
        lines.append(f"{item['data_hora']} | {item['servico'] or 'Serviço'} | {item['status']} | R$ {item['preco']:.2f}")
    lines.extend(["", "Avaliações"])
    for item in data["avaliacoes"]:
        lines.append(f"{item['criada_em']} | Nota: {item['nota']} | {item['comentario'] or ''}")
    lines.extend(["", "Consentimentos"])
    for item in data["consentimentos"]:
        lines.append(f"{item['aceito_em']} | Termos: {item['versao_termos']}")
    # At 11pt Helvetica, the widest supported glyph is <= 1.015 em.
    # A conservative bound fits every supported glyph inside the 515pt area.
    wrapped = [part for line in lines for part in (textwrap.wrap(line, 45) or [""])]
    pages = [wrapped[i:i+46] for i in range(0, len(wrapped), 46)]
    objects = [b"", b"", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"]
    kids = []
    for page in pages:
        page_id = len(objects) + 1
        kids.append(f"{page_id} 0 R")
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {page_id+1} 0 R >>".encode())
        commands = [b"BT /F1 11 Tf 40 800 Td 16 TL"]
        for line in page:
            safe = " ".join(line.split()).encode("cp1252")
            safe = safe.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
            commands.append(b"(" + safe + b") Tj T*")
        stream = b"\n".join(commands + [b"ET"])
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[1] = f"<< /Type /Pages /Count {len(kids)} /Kids [{' '.join(kids)}] >>".encode()
    result = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(result)
    result.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        result.extend(f"{offset:010d} 00000 n \n".encode())
    result.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(result)
