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

# --- CSS CUSTOMIZADO ---
st.markdown("""
    <style>
    .stApp { background-color: #f4f6f9; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: bold; color: #004d40; }
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        border: 1px solid #ced4da !important;
        border-radius: 6px !important;
        background-color: #ffffff !important;
        padding: 8px 12px !important;
    }
    div[data-testid="stDownloadButton"] > button {
        background-color: #004d40; color: white; border-radius: 8px;
        width: 100%; height: 55px; font-size: 16px; font-weight: bold; border: none; transition: 0.3s;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-top: 15px;
    }
    div[data-testid="stDownloadButton"] > button:hover {
        background-color: #00332a; box-shadow: 0 6px 12px rgba(0,0,0,0.2);
    }
    h1, h2, h3 { color: #004d40 !important; }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES ---
def formatar_nome_arquivo(empresa, comprador, referencia):
    empresa_u = empresa.upper()
    base = "FIRESTONE" if "BRIDGESTONE" in empresa_u or "FIRESTONE" in empresa_u else empresa_u.split()[0]
    return f"{base} - {comprador.upper()} - {referencia.upper()}.pdf"

def obter_data_ptbr():
    meses = {1: 'JANEIRO', 2: 'FEVEREIRO', 3: 'MARÇO', 4: 'ABRIL', 5: 'MAIO', 6: 'JUNHO',
             7: 'JULHO', 8: 'AGOSTO', 9: 'SETEMBRO', 10: 'OUTUBRO', 11: 'NOVEMBRO', 12: 'DEZEMBRO'}
    hoje = datetime.datetime.now()
    return f"SÃO PAULO, {hoje.day:02d} DE {meses[hoje.month]} DE {hoje.year}"

def gerar_corpo_pdf(dados, itens_df):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=45*mm, bottomMargin=40*mm)
    
    styles = getSampleStyleSheet()
    # PADRÃO ÚNICO PARA TUDO: Helvetica, tamanho 10, sem negrito
    style_normal = ParagraphStyle('Normal', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=14, textTransform='uppercase')
    
    elementos = []

    elementos.append(Paragraph(obter_data_ptbr(), style_normal))
    elementos.append(Spacer(1, 10*mm))
    
    texto_destinatario = f"A<br/>{dados['empresa']}<br/>{dados['local']}"
    elementos.append(Paragraph(texto_destinatario, style_normal))
    elementos.append(Spacer(1, 5*mm))
    
    texto_att = f"ATT. SR(A). {dados['comprador']} - COMPRAS<br/>REF. COTAÇÃO NO. {dados['ref_numero']}"
    elementos.append(Paragraph(texto_att, style_normal))
    elementos.append(Spacer(1, 8*mm))
    
    elementos.append(Paragraph("DAMOS ABAIXO, NOSSAS CONDIÇÕES PARA FORNECIMENTO DOS SEGUINTES MATERIAIS:", style_normal))
    elementos.append(Spacer(1, 5*mm))

    # 4. Tabela de Itens (Calibrada para evitar esmagamento)
    data = [["ITEM", "QUANT.", "UN. MED.", "DESCRIÇÃO", "GARANTIA", "PRAZO\nENTREGA", "V. UNIT.", "V. TOTAL"]]
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
            f"R$ {v_unit:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            f"R$ {v_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        ])

    linha_total = ["VALOR DA PROPOSTA", "", "", "", "", "", "", f"R$ {total_proposta:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")]
    data.append(linha_total)

    # Larguras totais (170mm)
    tabela = Table(data, colWidths=[10*mm, 15*mm, 15*mm, 45*mm, 20*mm, 20*mm, 22*mm, 23*mm])
    tabela.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('ALIGN', (0,0), (-1,-2), 'CENTER'),
        ('ALIGN', (3,1), (3,-2), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        
        # AFASTAMENTO DOS TÍTULOS (PADDING)
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('LEFTPADDING', (0,0), (-1,0), 4),
        ('RIGHTPADDING', (0,0), (-1,0), 4),
        
        # GRID SOMENTE ATÉ A PENÚLTIMA LINHA (Remove a linha de separação final)
        ('GRID', (0,0), (-1,-2), 0.5, colors.grey),
        
        # Estilo do Total
        ('SPAN', (0,-1), (6,-1)),
        ('ALIGN', (0,-1), (6,-1), 'RIGHT'),
        ('ALIGN', (7,-1), (7,-1), 'CENTER'),
        ('LINEBELOW', (7,-1), (7,-1), 0.5, colors.grey),
        ('LINEABOVE', (7,-1), (7,-1), 0.5, colors.grey),
        ('LEFTPADDING', (0,-1), (-1,-1), 4),
        ('RIGHTPADDING', (0,-1), (-1,-1), 4),
    ]))
    elementos.append(tabela)
    elementos.append(Spacer(1, 10*mm))

    # 5. Condições Comerciais (Um embaixo do outro, sem negrito)
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
        Spacer(1, 15*mm), # Espaço garantido entre Atenciosamente e o Nome
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

aba_nova, aba_hist, aba_config = st.tabs(["📄 Nova Proposta", "📂 Histórico", "⚙️ Configurações"])

with aba_nova:
    with st.container(border=True):
        st.subheader("Dados do Cliente")
        c1, c2 = st.columns(2)
        with c1:
            f_empresa = st.text_input("Razão Social do Cliente", placeholder="Ex: BRIDGESTONE / FIRESTONE")
            f_comprador = st.text_input("Comprador(a)", placeholder="Ex: NOME DO COMPRADOR")
            f_local = st.text_input("Cidade / UF", value="SAO PAULO/SP")
        with c2:
            f_ref = st.text_input("REF. COTAÇÃO NO.", placeholder="Ex: 123456")
            f_assinatura = st.selectbox("Assinatura", ["MILENE BUENO", "FELIPE"])

    with st.container(border=True):
        st.subheader("Itens da Cotação")
        df_itens = st.data_editor(
            pd.DataFrame([{"QUANT.": 1, "UN. MED.": "UN", "DESCRIÇÃO": "", "GARANTIA": "90 DIAS", "PRAZO ENTREGA": "25 DIAS", "VALOR UNIT.": 0.0}]),
            num_rows="dynamic", use_container_width=True,
            column_config={
                "QUANT.": st.column_config.NumberColumn(format="%d"),
                "VALOR UNIT.": st.column_config.NumberColumn(format="%.2f")
            }
        )

    with st.container(border=True):
        st.subheader("Condições Comerciais")
        c3, c4 = st.columns(2)
        with c3:
            f_marca = st.text_input("Marca Cotada", placeholder="Ex: HYUNDAI, VOLVO...")
            f_pagto = st.text_input("Pagamento", value="30 DIAS (DDF)")
            f_local_entrega = st.text_input("Local de Entrega", value="MATERIAL POSTO NO ALMOX. DA BRASFELS NO RJ. (CIF)")
        with c4:
            f_icms = st.text_input("ICMS (%)", value="12")
            f_ncm = st.text_input("NCM", value="8479.89.99")

    if f_empresa and f_comprador and f_ref:
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
        st.download_button("📥 BAIXAR PROPOSTA OFICIAL", data=pdf_final, file_name=nome_arq)
    else:
        st.warning("⚠️ Preencha os campos obrigatórios para liberar o download.")

with aba_hist:
    st.info("Histórico aguardando ativação do Supabase.")

with aba_config:
    st.write("Papel timbrado em: `assets/PAPEL TIMBRADO - JNL.pdf`")