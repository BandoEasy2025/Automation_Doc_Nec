"""
Configuration settings for the grant documentation crawler.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Database tables
BANDI_TABLE = "bandi"

# Request settings
REQUEST_TIMEOUT = 60  # seconds, increased for thorough processing
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
}
# the Accept-language header is set to italian to prioritize italian content 
# and to avoid issues with language detection 
# (e.g. some websites may have multiple languages and the default language may not be italian) 
# Retry settings
MAX_RETRIES = 5  # increased for reliability
RETRY_BACKOFF = 2  # seconds

# PDF processing
PDF_DOWNLOAD_DIR = "downloads/pdfs"
MAX_PDF_SIZE = 30 * 1024 * 1024  # 30 MB, increased for comprehensive PDFs

# Grant information search terms (in Italian) - enhanced with documentation focus
SEARCH_TERMS = [
    # Documentation terms
    "documentazione", "documenti", "allegati", "modulistica", "certificazioni",
    "domanda", "application", "modulo", "form", "istanza",
    "presentazione", "dichiarazione", "attestazione", "certification",
    "firma", "signature", "digitale", "identità", "identity",
    
    # General grant terms
    "bando", "contributo", "finanziamento", "sovvenzione", "agevolazione",
    "scadenza", "deadline", "termine", "presentazione", "domanda",
    "beneficiari", "destinatari", "requisiti", "ammissibilità", "eligibilità",
    "fondo", "misura", "intervento", "programma", "progetto",
    "spese", "costi", "ammissibili", "finanziabili", "contributo",
    "istruttoria", "valutazione", "punteggio", "criteri", "graduatoria",
    "erogazione", "rendicontazione", "liquidazione", "saldo", "anticipo",
    "visura", "camerale", "bilanci", "ula", "dipendenti",
    "brevetto", "patent", "concessione", "titolo", "invention",
    "servizi", "specialistici", "preventivi", "quotation", "valorizzazione"
]

# Important sections to look for - enhanced for documentation focus
IMPORTANT_SECTIONS = [
    # Documentation-specific sections
    "documentazione", "documenti", "allegati", "modulistica", 
    "come presentare", "presentazione domanda", "procedura",
    "documenti necessari", "certificazioni", "dichiarazioni",
    "domanda di partecipazione", "application form",
    
    # General grant sections
    "oggetto", "finalità", "obiettivi", "beneficiari", "destinatari",
    "requisiti", "allegati", "modalità", "presentazione",
    "scadenza", "termine", "dotazione", "finanziaria", "contributo",
    "agevolazione", "spese", "ammissibili", "istruttoria", "valutazione",
    "erogazione", "rendicontazione", "contatti", "informazioni", "faq"
]

# Documentation-specific patterns
DOCUMENTATION_PATTERNS = [
    r'document[azio\-\s]+necessari[ao]',
    r'allegat[io][\s]+(?:richiest[io]|necessari[io])',
    r'documentazione[\s]+da[\s]+(?:presentare|allegare)',
    r'documenti[\s]+(?:da[\s]+)?(?:presentare|allegare)',
    r'(?:modalit[aà]|procedura)[\s]+(?:di[\s]+)?presentazione',
    r'(?:domanda|istanza)[\s]+di[\s]+partecipazione',
    r'modulistic[ao]',
    r'certificazion[ei][\s]+(?:necessari[ae]|richiest[ae])',
    r'prerequisiti[\s]+documentali'
]

# PDF link patterns
PDF_LINK_PATTERNS = [
    r'.*\.pdf$',
    r'.*document.*\.pdf',
    r'.*allegat.*\.pdf',
    r'.*modulistic.*\.pdf',
    r'.*bando.*\.pdf',
    r'.*avviso.*\.pdf',
    r'.*decreto.*\.pdf',
    r'.*circolare.*\.pdf',
    r'.*istruzion.*\.pdf',
    r'.*guid.*\.pdf',
    r'.*regolament.*\.pdf',
    r'.*dichiaraz.*\.pdf',
    r'.*domanda.*\.pdf',
    r'.*istanza.*\.pdf',
    r'.*application.*\.pdf',
    r'.*form.*\.pdf'
]

# Important PDF types to prioritize
PRIORITY_PDF_PATTERNS = [
    'bando', 'avviso', 'decreto', 'documenti', 'allegat', 'modulistic', 
    'istruzion', 'guid', 'faq', 'regolament', 'domanda', 'application',
    'dichiaraz', 'attestaz', 'form', 'modul', 'certific'
]

# Documentation keywords (specific focus for extracting documentation requirements)
DOCUMENTATION_KEYWORDS = [
    'document', 'allegat', 'modulistic', 'certificaz', 
    'richiest', 'presentare', 'obbligo', 'necessari',
    'domanda', 'application', 'richiesta', 'presentazione',
    'firma', 'signature', 'digitale', 'copia', 'identity',
    'identità', 'dichiarazione', 'declaration', 'formulario',
    'modulo', 'form', 'attestazione', 'certification',
    'visura', 'camerale', 'obbligatori', 'facsimile',
    'istruzioni', 'formato', 'pdf', 'modello', 'template'
]