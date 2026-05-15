import streamlit as st
import pandas as pd
from io import BytesIO
import datetime

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from pypdf import PdfReader, PdfWriter

st.set_page_config(page_title="Sistema JNL - Propostas", layout="wide")

# --- CSS CUSTOMIZADO (Deixando bonito igual o Lovable) ---
st.markdown("""
    <style>
    /* Fundo da tela cinza claro */
    .stApp { background-color: #f0f2f5; }
    
    /* Caixas de formulário brancas com sombra */
    div[data-testid="stForm"] {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 25px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        border-top: 6px solid #004d40;
    }
    
    /* Botão Verde Escuro Moderno */
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #004d40;
        color: white;
        border-radius: 8px;
        width: 100%;
        height: 50px;
        font-weight: bold;
        border: none;
        transition: 0.3s;
    }
    div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #00332a;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Textos secundários em tons de cinza/verde */
    h1, h2, h3 { color: #004d40 !important; }
    label { color: #424242 !important; font-weight: 500 !important; }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES ---
def formatar_nome_arquivo(empresa, comprador, referencia):
    empresa_u = empresa.upper()
    base = "FIRESTONE" if "BRIDGESTONE" in empresa_u or "FIRESTONE" in empresa_u else empresa_u.split()[0]
    return f"{base} - {comprador.upper()} - {referencia.upper()}.pdf"

def gerar_corpo_pdf(dados, itens_df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=45*mm, bottomMargin=40*mm)
    
    styles = getSampleStyleSheet()
    # TUDO SEM NEGRITO, MESMA FONTE, MESMO TAMANHO (10)
    style_normal = ParagraphStyle('Normal', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=14, textTransform='uppercase')
    
    elementos = []

    # 1. Data
    data_hoje = datetime.datetime.now().strftime("SÃO PAULO, %d DE %B DE %Y").upper()
    elementos.append(Paragraph(data_hoje, style_normal))
    elementos.append(Spacer(1, 10*mm))
    
    # 2. Cliente (Tudo agrupado para não ter espaços extras)
    texto_destinatario = f"A<br/>{dados['empresa']}<br/>{dados['local']}"
    elementos.append(Paragraph(texto_destinatario, style_normal))
    elementos.append(Spacer(1, 5*mm))
    
    # 3. Comprador e Referência colados (Sem espaço isolado)
    texto_att = f"ATT. SR(A). {dados['comprador']} - COMPRAS<br/>REF. COTAÇÃO NO. {dados['ref_numero']}"
    elementos.append(Paragraph(texto_att, style_normal))
    elementos.append(Spacer(1, 8*mm))
    
    elementos.append(Paragraph("DAMOS ABAIXO, NOSSAS CONDIÇÕES PARA FORNECIMENTO DOS SEGUINTES MATERIAIS:", style_normal))
    elementos.append(Spacer(1, 5*mm))

    # 4. Tabela com VALORES TOTAIS
    data = [["ITEM", "QUANT.", "UN. MED.", "DESCRIÇÃO", "GARANTIA", "PRAZO ENTREGA", "UNIT.", "V. TOTAL"]]
    total_proposta = 0.0
    
    for i, row in itens_df.iterrows():
        qtd = float(row['QUANT.'])
        v_unit = float(row['VALOR UNIT.'])
        v_total = qtd * v_unit
        total_proposta += v_total
        
        desc_formatada = f"{row['DESCRIÇÃO']} - MARCA: {dados['marca']}"
        data.append([
            f"{i+1:02d}", str(int(qtd)), row['UN. MED.'], Paragraph(desc_formatada, style_normal), 
            row['GARANTIA'], row['PRAZO ENTREGA'], 
            f"R$ {v_unit:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), # Formato BR
            f"R$ {v_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        ])

    # Linha do Valor da Proposta
    linha_total = ["", "", "", "", "", "", "VALOR DA PROPOSTA", f"R$ {total_proposta:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")]
    data.append(linha_total)

    tabela = Table(data, colWidths=[9*mm, 14*mm, 16*mm, 45*mm, 20*mm, 25*mm, 20*mm, 22*mm])
    tabela.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'), # Sem negrito nem no cabeçalho
        ('FONTSIZE', (0,0), (-1,-1), 8), # Tabela um pouco menor para caber tudo
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-2), 0.5, colors.grey), # Linhas em tudo menos no total vazio
        ('LINEBELOW', (-2,-1), (-1,-1), 0.5, colors.grey), # Linha só no total
        ('LINEABOVE', (-2,-1), (-1,-1), 0.5, colors.grey),
    ]))
    elementos.append(tabela)
    elementos.append(Spacer(1, 10*mm))

    # 5. Bloco Comercial EXATAMENTE como pedido (Keep Together)
    bloco_final = [
        Paragraph(f"MARCA COTADA: {dados['marca']}", style_normal),
        Spacer(1, 5*mm),
        Paragraph(f"• CONDIÇÕES DE PAGAMENTO: {dados['pagamento']}", style_normal),
        Paragraph("• ALIQUOTA DE IPI: 0%", style_normal),
        Paragraph(f"• ICMS: {dados['icms']}% (INCLUSO NOS PREÇOS COTADOS)", style_normal),
        Paragraph(f"• NCM: {dados['ncm']}", style_normal),
        Paragraph("• VALIDADE DA PROPOSTA: 45 DIAS", style_normal),
        Paragraph(f"• {dados['local_entrega']}", style_normal),
        Spacer(1, 15*mm),
        Paragraph("ATENCIOSAMENTE,", style_normal),
        Paragraph(dados['assinatura_nome'], style_normal),
        Paragraph(dados['assinatura_cargo'], style_normal),
    ]
    elementos.append(KeepTogether(bloco_final))

    doc.build(elementos)
    buffer.seek(0)
    return buffer

def mesclar_com_timbre(buffer_texto):
    try:
        timbre_reader = PdfReader("assets/PAPEL TIMBRADO - JNL.pdf")
        texto_reader = PdfReader(buffer_texto)
        writer = PdfWriter()
        for page in texto_reader.pages:
            new_page = timbre_reader.pages[0]
            new_page.merge_page(page)
            writer.add_page(new_page)
        saida = BytesIO()
        writer.write(saida)
        saida.seek(0)
        return saida
    except:
        return buffer_texto

# --- INTERFACE ---
st.title("Centro de Comando JNL")

with st.form("form_vendas"):
    st.write("### Dados do Cliente")
    c1, c2 = st.columns(2)
    with c1:
        f_empresa = st.text_input("Razão Social do Cliente")
        f_comprador = st.text_input("Comprador(a)")
        f_local = st.text_input("Cidade / UF", value="SAO PAULO/SP")
    with c2:
        # Removido as opções RC e REF. Fixo agora.
        f_ref = st.text_input("REF. COTAÇÃO NO.")
        f_assinatura = st.selectbox("Assinatura", ["MILENE BUENO", "FELIPE"])

    st.write("### Itens da Cotação")
    df_itens = st.data_editor(
        pd.DataFrame([{"QUANT.": 1, "UN. MED.": "UN", "DESCRIÇÃO": "", "GARANTIA": "90 DIAS", "PRAZO ENTREGA": "25 DIAS", "VALOR UNIT.": 0.0}]),
        num_rows="dynamic", use_container_width=True,
        column_config={
            "QUANT.": st.column_config.NumberColumn(format="%d"),
            "VALOR UNIT.": st.column_config.NumberColumn(format="%.2f")
        }
    )

    st.write("### Condições Comerciais")
    c3, c4 = st.columns(2)
    with c3:
        f_marca = st.text_input("Marca Cotada")
        f_pagto = st.text_input("Pagamento", value="30 DIAS (DDF)")
        f_local_entrega = st.text_input("Local de Entrega", value="MATERIAL POSTO NO ALMOX. DA BRASFELS NO RJ. (CIF)")
    with c4:
        f_icms = st.text_input("ICMS (%)", value="12")
        f_ncm = st.text_input("NCM", value="8479.89.99")

    gerar = st.form_submit_button("GERAR PROPOSTA OFICIAL")

if gerar:
    payload = {
        'empresa': f_empresa.upper(), 'comprador': f_comprador.upper(), 'local': f_local.upper(),
        'ref_numero': f_ref.upper(), 'marca': f_marca.upper(),
        'pagamento': f_pagto.upper(), 'ncm': f_ncm, 'icms': f_icms, 'local_entrega': f_local_entrega.upper(),
        'assinatura_nome': f_assinatura,
        'assinatura_cargo': "ASSISTENTE COMERCIAL" if f_assinatura == "MILENE BUENO" else "DIRETOR"
    }
    
    pdf_corpo = gerar_corpo_pdf(payload, df_itens)
    pdf_final = mesclar_com_timbre(pdf_corpo)
    nome_arq = formatar_nome_arquivo(f_empresa, f_comprador, f_ref)
    
    st.success(f"Proposta gerada: {nome_arq}")
    st.download_button("📥 BAIXAR PDF OFICIAL", data=pdf_final, file_name=nome_arq)