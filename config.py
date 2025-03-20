"""
Configuration settings for the grant documentation crawler.
Enhanced with specific documentation requirements checklist.
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

# Specific documentation requirements to search for
REQUIRED_DOCUMENTATION = [
    {"name": "scheda progettuale", "keywords": ["scheda progett", "scheda del progett", "progett", "piano di sviluppo"]},
    {"name": "piano finanziario delle entrate e delle spese", "keywords": ["piano finanziar", "budget", "entrate e spese", "piano delle spese", "previsione di spesa"]},
    {"name": "programma di investimento", "keywords": ["programma di invest", "piano di invest", "investiment"]},
    {"name": "dichiarazione sul rispetto del DNSH", "keywords": ["DNSH", "Do No Significant Harm", "dichiarazione DNSH", "rispetto del DNSH"]},
    {"name": "copia delle ultime due dichiarazioni dei redditi", "keywords": ["dichiarazion", "redditi", "dichiarazione dei redditi", "modello unico", "modello 730"]},
    {"name": "dichiarazioni IVA", "keywords": ["IVA", "dichiarazione IVA", "dichiarazioni IVA", "imposta valore aggiunto"]},
    {"name": "situazione economica e patrimoniale", "keywords": ["situazione economic", "situazione patrimonial", "stato patrimonial", "bilancio", "conto economic"]},
    {"name": "conto economico previsionale", "keywords": ["conto economic", "economic prevision", "prevision", "bilancio prevision"]},
    {"name": "documenti giustificativi di spesa", "keywords": ["giustificativ", "spesa", "document di spesa", "fattur", "quietanz"]},
    {"name": "relazione dei lavori eseguiti", "keywords": ["relazione", "lavori eseguit", "relazione di esecuzione", "relazione tecnica"]},
    {"name": "materiale promozionale", "keywords": ["material promozional", "promozion", "marketing", "pubblicit"]},
    {"name": "informazioni su compagine sociale", "keywords": ["compagine social", "assetto societari", "soc", "struttura societaria"]},
    {"name": "elenco delle agevolazioni pubbliche", "keywords": ["agevolazion", "contribut", "finanziam", "aiuti di stato", "de minimis"]},
    {"name": "dichiarazione di inizio attività", "keywords": ["inizio attività", "DIA", "SCIA", "dichiarazione di inizio", "avvio attivit"]},
    {"name": "progetto imprenditoriale", "keywords": ["progetto imprenditori", "business idea", "idea imprenditori", "proposta imprenditori"]},
    {"name": "pitch", "keywords": ["pitch", "presentazione", "elevator pitch", "pitch deck"]},
    {"name": "curriculum vitae", "keywords": ["curriculum", "CV", "curriculum vitae", "esperienza", "competenze"]},
    {"name": "curriculum vitae team imprenditoriale", "keywords": ["curriculum team", "CV team", "team imprenditori", "soci", "fondatori"]},
    {"name": "dichiarazione sulla localizzazione", "keywords": ["localizzazione", "ubicazione", "sede", "luogo", "dichiarazione localizzazione"]},
    {"name": "atto di assenso del proprietario", "keywords": ["assenso", "propriet", "autorizzazione propriet", "consenso propriet"]},
    {"name": "contratto di locazione", "keywords": ["locazion", "affitto", "contratto di locazione", "contratto d'affitto"]},
    {"name": "contratto di comodato", "keywords": ["comodato", "comodato d'uso", "contratto di comodato"]},
    {"name": "certificazione qualità", "keywords": ["certificazione qualit", "ISO", "certificato di qualit", "sistema qualit"]},
    {"name": "fatture elettroniche", "keywords": ["fattur", "fattura elettronic", "fatturazione elettronic", "e-fattura"]},
    {"name": "quietanze originali", "keywords": ["quietanz", "ricevut", "pagament", "bonifico", "pagamento effettuato"]},
    {"name": "Business plan", "keywords": ["business plan", "piano di business", "piano aziendale", "piano d'impresa"]},
    {"name": "dichiarazione sostitutiva", "keywords": ["dichiarazione sostitutiva", "autocertificazione", "DPR 445", "445/2000"]},
    {"name": "copia dei pagamenti effettuati", "keywords": ["pagament", "bonifico", "estratto conto", "ricevuta di pagamento"]},
    {"name": "dichiarazione di fine corso", "keywords": ["fine corso", "completamento corso", "attestazione finale", "conclusione corso"]},
    {"name": "attestato di frequenza", "keywords": ["attestato", "frequenza", "partecipazione", "certificato di frequenza"]},
    {"name": "report di self-assessment SUSTAINability", "keywords": ["self-assessment", "sustainability", "sostenibilit", "valutazione sostenibilit"]},
    {"name": "relazione finale di progetto", "keywords": ["relazione final", "report final", "conclusione progett", "progetto concluso"]},
    {"name": "Atto di conferimento", "keywords": ["conferimento", "atto di conferimento", "conferimento incarico", "mandato"]},
    {"name": "investitore esterno", "keywords": ["investitor", "finanziator", "business angel", "venture capital", "investimento esterno"]},
    {"name": "Delega del Legale rappresentante", "keywords": ["delega", "legale rappresentante", "rappresentanza", "procura"]},
    {"name": "Budget dei costi", "keywords": ["budget", "costi", "preventivo", "piano dei costi", "previsione costi"]},
    {"name": "Certificato di attribuzione del codice fiscale", "keywords": ["codice fiscale", "certificato attribuzione", "attribuzione codice", "agenzia entrate"]},
    {"name": "Analisi delle entrate", "keywords": ["analisi entrate", "entrate", "ricavi", "introiti", "analisi ricavi"]},
    {"name": "DURC", "keywords": ["DURC", "regolarità contributiva", "documento unico", "contributi"]},
    {"name": "Dichiarazione antiriciclaggio", "keywords": ["antiriciclaggio", "riciclaggio", "AML", "D.lgs 231"]},
    {"name": "Dichiarazioni antimafia", "keywords": ["antimafia", "certificazione antimafia", "informativa antimafia", "D.lgs 159"]},
    {"name": "fideiussione", "keywords": ["fideiussion", "garanzia", "polizza fideiussoria", "garanzia bancaria"]},
    {"name": "Casellario Giudiziale", "keywords": ["casellario", "giudiziale", "certificato penale", "carichi pendenti"]},
    {"name": "Fideiussione Provvisoria", "keywords": ["fideiussione provvisoria", "garanzia provvisoria", "cauzione provvisoria"]},
    {"name": "contributo ANAC", "keywords": ["ANAC", "autorità anticorruzione", "contributo gara"]},
    {"name": "DICHIARAZIONE D'INTENTI", "keywords": ["intenti", "dichiarazione d'intenti", "lettera d'intenti", "manifestazione interesse"]},
    {"name": "DICHIARAZIONE INTESTAZIONE FIDUCIARIA", "keywords": ["intestazione fiduciaria", "fiduciari", "trustee", "fiduciante"]},
    {"name": "certificato di regolarità fiscale", "keywords": ["regolarità fiscal", "agenzia entrate", "debiti fiscali", "imposte"]},
    {"name": "certificato di iscrizione al registro delle imprese", "keywords": ["registro imprese", "iscrizione camera", "CCIAA", "camera di commercio"]},
    {"name": "piano di sicurezza", "keywords": ["sicurezza", "piano di sicurezza", "PSC", "coordinamento sicurezza"]},
    {"name": "certificato di conformità", "keywords": ["conformità", "certificato conformità", "dichiarazione conformità", "attestazione conformità"]},
    {"name": "Attestazione del professionista", "keywords": ["attestazione professionist", "perizia", "relazione professionist", "relazione tecnica"]},
    {"name": "GANTT del progetto", "keywords": ["gantt", "cronoprogramma", "tempistiche", "pianificazione temporale"]},
    {"name": "atto di nomina", "keywords": ["nomina", "atto di nomina", "designazione", "incarico"]},
    {"name": "visura catastale", "keywords": ["visura catast", "catasto", "dati catastali", "estratto catastale"]},
    {"name": "DSAN", "keywords": ["DSAN", "dichiarazione sostitutiva atto notorietà", "atto notorio", "dichiarazione sostitutiva"]},
    {"name": "certificato di attribuzione di partita IVA", "keywords": ["partita IVA", "P.IVA", "attribuzione IVA", "certificato IVA"]},
    {"name": "brevetto", "keywords": ["brevett", "patent", "proprietà intellettuale", "invenzione"]},
    {"name": "licenza brevettuale", "keywords": ["licenza brevett", "licenza patent", "uso brevetto", "sfruttamento brevetto"]},
    {"name": "attestato di certificazione del libretto", "keywords": ["libretto", "libretto di certificazione", "libretto formativo", "attestato libretto"]},
    {"name": "visura camerale", "keywords": ["visura", "visura camerale", "camera di commercio", "registro imprese"]},
    {"name": "carta d'identità", "keywords": ["carta d'identità", "documento identità", "carta identità", "ID"]},
    {"name": "codice fiscale", "keywords": ["codice fiscale", "CF", "tessera sanitaria", "codice contribuente"]},
    {"name": "certificato Soa", "keywords": ["SOA", "attestazione SOA", "qualificazione", "certificato SOA"]}
]

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