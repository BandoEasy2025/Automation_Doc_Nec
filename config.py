# """
# Configuration settings for the grant documentation crawler.
# Enhanced with specific documentation item keywords to search for.
# """
# import os
# from dotenv import load_dotenv

# # Load environment variables from .env file
# load_dotenv()

# # Supabase configuration
# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# # Database tables
# BANDI_TABLE = "bandi"

# # Request settings
# REQUEST_TIMEOUT = 60  # seconds, increased for thorough processing
# REQUEST_HEADERS = {
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
#     "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
# }

# # Retry settings
# MAX_RETRIES = 5  # increased for reliability
# RETRY_BACKOFF = 2  # seconds

# # PDF processing
# PDF_DOWNLOAD_DIR = "downloads/pdfs"
# MAX_PDF_SIZE = 30 * 1024 * 1024  # 30 MB, increased for comprehensive PDFs

# # Specific documentation items to search for - these are the exact items we want to detect
# DOCUMENTATION_ITEMS = [
#     {"name": "scheda progettuale", "keywords": ["scheda progett", "scheda del progett", "scheda tecnica del progett"]},
#     {"name": "piano finanziario delle entrate e delle spese", "keywords": ["piano finanziar", "entrate e spese", "budget", "piano economico"]},
#     {"name": "programma di investimento", "keywords": ["programma di invest", "piano di invest", "investiment"]},
#     {"name": "dichiarazione sul rispetto del DNSH", "keywords": ["DNSH", "Do No Significant Harm", "dichiarazione DNSH"]},
#     {"name": "dichiarazioni dei redditi", "keywords": ["dichiarazion dei redditi", "modello redditi", "dichiarazione fiscale"]},
#     {"name": "dichiarazioni IVA", "keywords": ["dichiarazion IVA", "IVA", "imposta sul valore aggiunto"]},
#     {"name": "situazione economica e patrimoniale", "keywords": ["situazione economic", "situazione patrimonial", "stato patrimonial"]},
#     {"name": "conto economico previsionale", "keywords": ["conto economic", "previsional", "bilancio prevision"]},
#     {"name": "documenti giustificativi di spesa", "keywords": ["giustificativ", "document di spesa", "fattur"]},
#     {"name": "relazione dei lavori eseguiti", "keywords": ["relazione", "lavori eseguit", "relazione tecnica"]},
#     {"name": "materiale promozionale", "keywords": ["material promozional", "promozion", "marketing"]},
#     {"name": "informazioni su compagine sociale", "keywords": ["compagine social", "assetto societari", "soci"]},
#     {"name": "elenco delle agevolazioni pubbliche", "keywords": ["agevolazion", "contribut", "de minimis"]},
#     {"name": "dichiarazione di inizio attività", "keywords": ["inizio attività", "DIA", "SCIA"]},
#     {"name": "progetto imprenditoriale", "keywords": ["progetto imprenditori", "business idea", "idea imprenditori"]},
#     {"name": "pitch", "keywords": ["pitch", "presentazione", "elevator pitch"]},
#     {"name": "curriculum vitae", "keywords": ["curriculum", "CV", "curriculum vitae"]},
#     {"name": "curriculum vitae team imprenditoriale", "keywords": ["curriculum team", "CV team", "team imprenditori"]},
#     {"name": "dichiarazione sulla localizzazione", "keywords": ["localizzazione", "ubicazione", "sede"]},
#     {"name": "atto di assenso del proprietario", "keywords": ["assenso", "propriet", "autorizzazione propriet"]},
#     {"name": "contratto di locazione", "keywords": ["locazion", "affitto", "contratto di locazione"]},
#     {"name": "contratto di comodato", "keywords": ["comodato", "comodato d'uso", "contratto di comodato"]},
#     {"name": "certificazione qualità", "keywords": ["certificazione qualit", "ISO", "certificato di qualit"]},
#     {"name": "fatture elettroniche", "keywords": ["fattur elettronic", "e-fattura", "fatturazione elettronic"]},
#     {"name": "quietanze originali", "keywords": ["quietanz", "ricevut", "pagament"]},
#     {"name": "Business plan", "keywords": ["business plan", "piano di business", "piano aziendale"]},
#     {"name": "dichiarazione sostitutiva dell'atto di notorietà", "keywords": ["dichiarazione sostitutiva", "atto di notorietà", "DPR 445"]},
#     {"name": "copia dei pagamenti effettuati", "keywords": ["pagament", "bonifico", "estratto conto"]},
#     {"name": "dichiarazione di fine corso", "keywords": ["fine corso", "completamento corso", "attestazione finale"]},
#     {"name": "attestato di frequenza", "keywords": ["attestato", "frequenza", "partecipazione"]},
#     {"name": "report di self-assessment SUSTAINability", "keywords": ["self-assessment", "sustainability", "sostenibilit"]},
#     {"name": "relazione finale di progetto", "keywords": ["relazione final", "report final", "conclusione progett"]},
#     {"name": "Atto di conferimento", "keywords": ["conferimento", "atto di conferimento", "conferimento incarico"]},
#     {"name": "investitore esterno", "keywords": ["investitor", "finanziator", "business angel"]},
#     {"name": "Delega del Legale rappresentante", "keywords": ["delega", "legale rappresentante", "rappresentanza"]},
#     {"name": "Budget dei costi", "keywords": ["budget", "costi", "preventivo"]},
#     {"name": "Certificato di attribuzione del codice fiscale", "keywords": ["codice fiscale", "certificato attribuzione", "attribuzione codice"]},
#     {"name": "Analisi delle entrate", "keywords": ["analisi entrate", "entrate", "ricavi"]},
#     {"name": "DURC", "keywords": ["DURC", "regolarità contributiva", "documento unico"]},
#     {"name": "Dichiarazione antiriciclaggio", "keywords": ["antiriciclaggio", "riciclaggio", "AML"]},
#     {"name": "Dichiarazioni antimafia", "keywords": ["antimafia", "certificazione antimafia", "informativa antimafia"]},
#     {"name": "fideiussione", "keywords": ["fideiussion", "garanzia", "polizza fideiussoria"]},
#     {"name": "Casellario Giudiziale", "keywords": ["casellario", "giudiziale", "certificato penale"]},
#     {"name": "Fideiussione Provvisoria", "keywords": ["fideiussione provvisoria", "garanzia provvisoria", "cauzione provvisoria"]},
#     {"name": "contributo ANAC", "keywords": ["ANAC", "autorità anticorruzione", "contributo gara"]},
#     {"name": "DICHIARAZIONE D'INTENTI", "keywords": ["intenti", "dichiarazione d'intenti", "lettera d'intenti"]},
#     {"name": "DICHIARAZIONE INTESTAZIONE FIDUCIARIA", "keywords": ["intestazione fiduciaria", "fiduciari", "trustee"]},
#     {"name": "certificato di regolarità fiscale", "keywords": ["regolarità fiscal", "agenzia entrate", "debiti fiscali"]},
#     {"name": "certificato di iscrizione al registro delle imprese", "keywords": ["registro imprese", "iscrizione camera", "CCIAA"]},
#     {"name": "piano di sicurezza e coordinamento", "keywords": ["sicurezza", "piano di sicurezza", "PSC"]},
#     {"name": "certificato di conformità", "keywords": ["conformità", "certificato conformità", "dichiarazione conformità"]},
#     {"name": "Attestazione del professionista", "keywords": ["attestazione professionist", "perizia", "relazione professionist"]},
#     {"name": "GANTT del progetto", "keywords": ["gantt", "cronoprogramma", "tempistiche"]},
#     {"name": "atto di nomina", "keywords": ["nomina", "atto di nomina", "designazione"]},
#     {"name": "visura catastale", "keywords": ["visura catast", "catasto", "dati catastali"]},
#     {"name": "DSAN", "keywords": ["DSAN", "dichiarazione sostitutiva atto notorietà", "atto notorio"]},
#     {"name": "certificato di attribuzione di partita IVA", "keywords": ["partita IVA", "P.IVA", "attribuzione IVA"]},
#     {"name": "brevetto", "keywords": ["brevett", "patent", "proprietà intellettuale"]},
#     {"name": "licenza brevettuale", "keywords": ["licenza brevett", "licenza patent", "uso brevetto"]},
#     {"name": "attestato di certificazione del libretto", "keywords": ["libretto", "libretto di certificazione", "libretto formativo"]},
#     {"name": "visura camerale", "keywords": ["visura", "visura camerale", "camera di commercio"]},
#     {"name": "carta d'identità", "keywords": ["carta d'identità", "documento identità", "carta identità"]},
#     {"name": "codice fiscale dei soci", "keywords": ["codice fiscale", "CF", "tessera sanitaria"]},
#     {"name": "certificato Soa", "keywords": ["SOA", "attestazione SOA", "qualificazione"]}
# ]

# # Grant information search terms (in Italian)
# SEARCH_TERMS = [
#     # Documentation terms
#     "documentazione", "documenti", "allegati", "modulistica", "certificazioni",
#     "domanda", "application", "modulo", "form", "istanza",
#     "presentazione", "dichiarazione", "attestazione", "certification",
#     "firma", "signature", "digitale", "identità", "identity",
    
#     # General grant terms
#     "bando", "contributo", "finanziamento", "sovvenzione", "agevolazione",
#     "scadenza", "deadline", "termine", "presentazione", "domanda",
#     "beneficiari", "destinatari", "requisiti", "ammissibilità", "eligibilità",
#     "fondo", "misura", "intervento", "programma", "progetto",
#     "spese", "costi", "ammissibili", "finanziabili", "contributo",
#     "istruttoria", "valutazione", "punteggio", "criteri", "graduatoria",
#     "erogazione", "rendicontazione", "liquidazione", "saldo", "anticipo"
# ]

# # Important sections to look for
# IMPORTANT_SECTIONS = [
#     # Documentation-specific sections
#     "documentazione", "documenti", "allegati", "modulistica", 
#     "come presentare", "presentazione domanda", "procedura",
#     "documenti necessari", "certificazioni", "dichiarazioni",
#     "domanda di partecipazione", "application form",
    
#     # General grant sections
#     "oggetto", "finalità", "obiettivi", "beneficiari", "destinatari",
#     "requisiti", "allegati", "modalità", "presentazione",
#     "scadenza", "termine", "dotazione", "finanziaria", "contributo",
#     "agevolazione", "spese", "ammissibili", "istruttoria", "valutazione",
#     "erogazione", "rendicontazione", "contatti", "informazioni", "faq"
# ]

# # Documentation-specific patterns
# DOCUMENTATION_PATTERNS = [
#     r'document[azio\-\s]+necessari[ao]',
#     r'allegat[io][\s]+(?:richiest[io]|necessari[io])',
#     r'documentazione[\s]+da[\s]+(?:presentare|allegare)',
#     r'documenti[\s]+(?:da[\s]+)?(?:presentare|allegare)',
#     r'(?:modalit[aà]|procedura)[\s]+(?:di[\s]+)?presentazione',
#     r'(?:domanda|istanza)[\s]+di[\s]+partecipazione',
#     r'modulistic[ao]',
#     r'certificazion[ei][\s]+(?:necessari[ae]|richiest[ae])',
#     r'prerequisiti[\s]+documentali'
# ]

# # PDF link patterns
# PDF_LINK_PATTERNS = [
#     r'.*\.pdf$',
#     r'.*document.*\.pdf',
#     r'.*allegat.*\.pdf',
#     r'.*modulistic.*\.pdf',
#     r'.*bando.*\.pdf',
#     r'.*avviso.*\.pdf',
#     r'.*decreto.*\.pdf',
#     r'.*circolare.*\.pdf',
#     r'.*istruzion.*\.pdf',
#     r'.*guid.*\.pdf',
#     r'.*regolament.*\.pdf',
#     r'.*dichiaraz.*\.pdf',
#     r'.*domanda.*\.pdf',
#     r'.*istanza.*\.pdf',
#     r'.*application.*\.pdf',
#     r'.*form.*\.pdf'
# ]

# # Important PDF types to prioritize
# PRIORITY_PDF_PATTERNS = [
#     'bando', 'avviso', 'decreto', 'documenti', 'allegat', 'modulistic', 
#     'istruzion', 'guid', 'faq', 'regolament', 'domanda', 'application',
#     'dichiaraz', 'attestaz', 'form', 'modul', 'certific'
# ]

# # Documentation keywords (specific focus for extracting documentation requirements)
# DOCUMENTATION_KEYWORDS = [
#     'document', 'allegat', 'modulistic', 'certificaz', 
#     'richiest', 'presentare', 'obbligo', 'necessari',
#     'domanda', 'application', 'richiesta', 'presentazione',
#     'firma', 'signature', 'digitale', 'copia', 'identity',
#     'identità', 'dichiarazione', 'declaration', 'formulario',
#     'modulo', 'form', 'attestazione', 'certification',
#     'visura', 'camerale', 'obbligatori', 'facsimile',
#     'istruzioni', 'formato', 'pdf', 'modello', 'template'
# ]

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