# -----------------------------------------------------------------------------
# Liste des flux RSS/Atom surveillés.
#
# Chaque entrée : (nom, url_flux, zone_par_defaut, theme_par_defaut, langue)
# La zone/thème par défaut sont des suggestions : le LLM reclasse ensuite chaque
# article individuellement. La langue sert de metadonnee (filtre, affichage) —
# elle n'est pas utilisee pour la traduction : le LLM produit toujours un
# resume en francais, quelle que soit la langue source de l'article.
#
# -> Cette liste est faite pour être éditée librement. Certains flux RSS
#    changent d'URL avec le temps : si un flux ne renvoie plus rien après
#    quelques jours (regarde /api/feeds ou les logs), vérifie son URL sur le
#    site de la source et corrige-la ici. Le fichier est monté en volume
#    (docker-compose.yml) donc une modification ne nécessite pas de
#    reconstruire l'image, juste un `docker compose restart sentinel`.
#
#    Fiabilité des URLs ci-dessous : les flux BBC (feeds.bbci.co.uk/<lang>/rss.xml)
#    et DW (rss.dw.com/rdf/rss-<lang>-...) suivent un format d'URL vérifié et
#    stable. Les autres sources (agences nationales, presse locale) suivent des
#    formats habituels mais n'ont pas toutes été testées une par une : si l'une
#    d'elles ne remonte rien, corrige juste son URL sans te soucier du reste.
# -----------------------------------------------------------------------------

FEEDS = [
    # ================================================================== FRANÇAIS
    ("Le Monde - International", "https://www.lemonde.fr/international/rss_full.xml", "Monde", "Diplomatie", "fr"),
    ("Courrier International - Monde", "https://www.courrierinternational.com/feed/all/rss.xml", "Monde", "Diplomatie", "fr"),
    ("France 24 - International", "https://www.france24.com/fr/rss", "Monde", "Diplomatie", "fr"),
    ("France 24 - Arabe", "https://www.france24.com/ar/rss", "Moyen-Orient", "Diplomatie", "ar"),
    ("France 24 - Espagnol", "https://www.france24.com/es/rss", "Amérique du Sud", "Diplomatie", "es"),
    ("RFI - International", "https://www.rfi.fr/fr/rss", "Monde", "Diplomatie", "fr"),
    ("RFI - Afrique", "https://www.rfi.fr/fr/afrique/rss", "Afrique", "Politique intérieure", "fr"),
    ("Le Figaro - International", "https://www.lefigaro.fr/rss/figaro_international.xml", "Monde", "Diplomatie", "fr"),
    ("Libération - Monde", "https://www.liberation.fr/arc/outboundfeeds/rss/category/monde/", "Monde", "Diplomatie", "fr"),
    ("Les Echos - Monde", "https://services.lesechos.fr/rss/les-echos-monde.xml", "Monde", "Économie", "fr"),
    ("Le Grand Continent", "https://legrandcontinent.eu/fr/feed/", "Europe", "Diplomatie", "fr"),
    ("IFRI - Publications", "https://www.ifri.org/fr/rss.xml", "Monde", "Diplomatie", "fr"),
    ("Opex360 (Lignes de Défense)", "http://www.opex360.com/feed/", "Monde", "Défense", "fr"),
    ("Jeune Afrique", "https://www.jeuneafrique.com/feed/", "Afrique", "Politique intérieure", "fr"),
    ("BBC Afrique (français)", "https://feeds.bbci.co.uk/afrique/rss.xml", "Afrique", "Politique intérieure", "fr"),
    ("Notes from Poland", "https://notesfrompoland.com/feed/", "Europe", "Politique intérieure", "en"),

    # ================================================================== ANGLAIS
    ("Reuters - World", "https://feeds.reuters.com/Reuters/worldNews", "Monde", "Politique intérieure", "en"),
    ("AP News - World", "https://apnews.com/hub/world-news.rss", "Monde", "Politique intérieure", "en"),
    ("BBC News - World", "http://feeds.bbci.co.uk/news/world/rss.xml", "Monde", "Politique intérieure", "en"),
    ("Al Jazeera English - All", "https://www.aljazeera.com/xml/rss/all.xml", "Monde", "Politique intérieure", "en"),
    ("Foreign Policy", "https://foreignpolicy.com/feed/", "Monde", "Diplomatie", "en"),
    ("Foreign Affairs", "https://www.foreignaffairs.com/rss.xml", "Monde", "Diplomatie", "en"),
    ("Chatham House - Publications", "https://www.chathamhouse.org/rss/publications", "Monde", "Diplomatie", "en"),
    ("Crisis Group - Latest", "https://www.crisisgroup.org/rss.xml", "Monde", "Diplomatie", "en"),
    ("ECFR - Publications", "https://ecfr.eu/feed/", "Europe", "Diplomatie", "en"),
    ("Carnegie Endowment", "https://carnegieendowment.org/rss/solr/?fa=events", "Monde", "Diplomatie", "en"),
    ("CSIS - Analysis", "https://www.csis.org/analysis/feed", "Monde", "Diplomatie", "en"),
    ("Council on Foreign Relations", "https://www.cfr.org/rss-feeds/rss.xml", "Amérique du Nord", "Diplomatie", "en"),
    ("Defense News", "https://www.defensenews.com/arc/outboundfeeds/rss/", "Monde", "Défense", "en"),
    ("War on the Rocks", "https://warontherocks.com/feed/", "Monde", "Défense", "en"),
    ("Breaking Defense", "https://breakingdefense.com/feed/", "Monde", "Défense", "en"),
    ("IISS - Analysis", "https://www.iiss.org/rss/analysis", "Monde", "Défense", "en"),
    ("NATO - News", "https://www.nato.int/cps/en/natohq/news.rss", "Europe", "Défense", "en"),
    ("Politico Europe", "https://www.politico.eu/feed/", "Europe", "Politique intérieure", "en"),
    ("EURACTIV", "https://www.euractiv.com/feed/", "Europe", "Politique intérieure", "en"),
    ("The Local Europe", "https://feeds.thelocal.com/rss/europe", "Europe", "Politique intérieure", "en"),
    ("Financial Times - World", "https://www.ft.com/world?format=rss", "Monde", "Économie", "en"),
    ("The Record (cybersécurité)", "https://therecord.media/feed/", "Monde", "Cybersécurité", "en"),
    ("Bleeping Computer", "https://www.bleepingcomputer.com/feed/", "Monde", "Cybersécurité", "en"),
    ("IEA - News", "https://www.iea.org/news/rss", "Monde", "Énergie", "en"),
    ("OilPrice.com", "https://oilprice.com/rss/main", "Monde", "Énergie", "en"),
    ("Atlantic Council DFRLab", "https://www.atlanticcouncil.org/programs/digital-forensic-research-lab/feed/", "Monde", "Ingérences étrangères", "en"),
    ("Middle East Eye", "https://www.middleeasteye.net/rss", "Moyen-Orient", "Sécurité", "en"),
    ("Al-Monitor", "https://www.al-monitor.com/rss", "Moyen-Orient", "Diplomatie", "en"),
    ("Times of Israel", "https://www.timesofisrael.com/feed/", "Moyen-Orient", "Sécurité", "en"),
    ("Jerusalem Post", "https://www.jpost.com/rss/rssfeedsfrontpage.aspx", "Moyen-Orient", "Sécurité", "en"),
    ("Asharq Al-Awsat (anglais)", "https://english.aawsat.com/feed", "Moyen-Orient", "Diplomatie", "en"),
    ("The Africa Report", "https://www.theafricareport.com/feed/", "Afrique", "Économie", "en"),
    ("ISS Africa - Today", "https://issafrica.org/rss/todayfeed", "Afrique", "Sécurité", "en"),
    ("AllAfrica - Headlines", "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf", "Afrique", "Politique intérieure", "en"),
    ("Premium Times Nigeria", "https://www.premiumtimesng.com/feed", "Afrique", "Politique intérieure", "en"),
    ("Daily Maverick Afrique du Sud", "https://www.dailymaverick.co.za/southafrica/feed/", "Afrique", "Politique intérieure", "en"),
    ("The Diplomat (Asie-Pacifique)", "https://thediplomat.com/feed/", "Asie", "Diplomatie", "en"),
    ("Nikkei Asia", "https://asia.nikkei.com/rss/feed/nar", "Asie", "Économie", "en"),
    ("South China Morning Post - China", "https://www.scmp.com/rss/318198/feed", "Asie", "Politique intérieure", "en"),
    ("The Hindu - International", "https://www.thehindu.com/news/international/feeder/default.rss", "Asie", "Diplomatie", "en"),
    ("Times of India - World", "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms", "Asie", "Politique intérieure", "en"),
    ("Dawn (Pakistan)", "https://www.dawn.com/feeds/home", "Asie", "Politique intérieure", "en"),
    ("Rappler (Philippines)", "https://www.rappler.com/feed/", "Asie", "Politique intérieure", "en"),
    ("Bangkok Post - World", "https://www.bangkokpost.com/rss/data/world.xml", "Asie", "Politique intérieure", "en"),
    ("Channel News Asia", "https://www.channelnewsasia.com/rssfeeds/8395986", "Asie", "Politique intérieure", "en"),
    ("ABC News Australia - Just In", "https://www.abc.net.au/news/feed/51120/rss.xml", "Océanie", "Politique intérieure", "en"),
    ("RNZ Pacific", "https://www.rnz.co.nz/rss/pacific.xml", "Océanie", "Politique intérieure", "en"),
    ("AP News - US Government", "https://apnews.com/hub/united-states-government.rss", "Amérique du Nord", "Politique intérieure", "en"),
    ("MercoPress (Amérique du Sud)", "https://en.mercopress.com/rss/", "Amérique du Sud", "Politique intérieure", "en"),
    ("Moscow Times", "https://www.themoscowtimes.com/rss/news", "Eurasie", "Politique intérieure", "en"),
    ("Meduza - EN", "https://meduza.io/rss/en/all", "Eurasie", "Politique intérieure", "en"),
    ("Kyiv Independent", "https://kyivindependent.com/feed/", "Eurasie", "Sécurité", "en"),
    ("Kyiv Post", "https://www.kyivpost.com/feed", "Eurasie", "Sécurité", "en"),
    ("RFE/RL - News", "https://www.rferl.org/api/zrqiteuuir", "Eurasie", "Politique intérieure", "en"),
    ("Iran International (anglais)", "https://www.iranintl.com/en/rss", "Moyen-Orient", "Sécurité", "en"),
    ("TASS (anglais)", "https://tass.com/rss/v2.xml", "Eurasie", "Politique intérieure", "en"),
    ("Xinhua - World (anglais)", "http://www.xinhuanet.com/english/rss/worldrss.xml", "Asie", "Politique intérieure", "en"),
    ("CGTN - World (anglais)", "https://www.cgtn.com/subscribe/rss/section/world.xml", "Asie", "Politique intérieure", "en"),
    ("RT (anglais)", "https://www.rt.com/rss/", "Eurasie", "Politique intérieure", "en"),
    ("Anadolu Agency (anglais)", "https://www.aa.com.tr/en/rss/default?cat=guncel", "Moyen-Orient", "Politique intérieure", "en"),

    # ================================================================== ESPAGNOL
    ("BBC Mundo", "https://feeds.bbci.co.uk/mundo/rss.xml", "Amérique du Sud", "Politique intérieure", "es"),
    ("El País - Internacional", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional", "Monde", "Diplomatie", "es"),
    ("El Mundo - Internacional", "https://e00-elmundo.uecdn.es/rss/internacional.xml", "Monde", "Diplomatie", "es"),
    ("Clarín - Mundo (Argentine)", "https://www.clarin.com/rss/mundo/", "Amérique du Sud", "Politique intérieure", "es"),
    ("Infobae - América", "https://www.infobae.com/arc/outboundfeeds/rss/category/america/", "Amérique du Sud", "Politique intérieure", "es"),
    ("DW Espagnol", "https://rss.dw.com/rdf/rss-es-all", "Amérique du Sud", "Diplomatie", "es"),
    ("RFI Espagnol", "https://www.rfi.fr/es/rss", "Amérique du Sud", "Diplomatie", "es"),
    ("Anadolu Agency (espagnol)", "https://www.aa.com.tr/es/rss/default?cat=guncel", "Moyen-Orient", "Politique intérieure", "es"),

    # ================================================================== PORTUGAIS
    ("BBC Brasil", "https://feeds.bbci.co.uk/portuguese/rss.xml", "Amérique du Sud", "Politique intérieure", "pt"),
    ("Folha de S.Paulo - Mundo", "https://feeds.folha.uol.com.br/mundo/rss091.xml", "Amérique du Sud", "Politique intérieure", "pt"),
    ("RFI Portugais", "https://www.rfi.fr/pt/rss", "Amérique du Sud", "Diplomatie", "pt"),

    # ================================================================== ALLEMAND
    ("DW - Actualités (allemand)", "https://rss.dw.com/rdf/rss-de-all", "Europe", "Diplomatie", "de"),
    ("Der Spiegel - International (anglais)", "https://www.spiegel.de/international/index.rss", "Europe", "Politique intérieure", "en"),
    ("Süddeutsche Zeitung - Politik", "https://rss.sueddeutsche.de/rss/Politik", "Europe", "Politique intérieure", "de"),

    # ================================================================== ITALIEN
    ("Corriere della Sera - Esteri", "https://xml2.corriereobjects.it/rss/esteri.xml", "Europe", "Diplomatie", "it"),
    ("La Repubblica - Esteri", "https://www.repubblica.it/rss/esteri/rss2.0.xml", "Europe", "Diplomatie", "it"),

    # ================================================================== NÉERLANDAIS / SCANDINAVE
    ("NOS - Buitenland (Pays-Bas)", "https://feeds.nos.nl/nosnieuwsbuitenland", "Europe", "Politique intérieure", "nl"),
    ("NRK - Verden (Norvège)", "https://www.nrk.no/verden/toppsaker.rss", "Europe", "Politique intérieure", "no"),

    # ================================================================== RUSSE
    ("BBC Russe", "https://feeds.bbci.co.uk/russian/rss.xml", "Eurasie", "Politique intérieure", "ru"),
    ("DW Russe", "https://rss.dw.com/rdf/rss-ru-all", "Eurasie", "Diplomatie", "ru"),
    ("Kommersant (Russie)", "https://www.kommersant.ru/RSS/news.xml", "Eurasie", "Économie", "ru"),
    ("TASS (russe)", "https://tass.ru/rss/v2.xml", "Eurasie", "Politique intérieure", "ru"),

    # ================================================================== UKRAINIEN
    ("BBC Ukrainien", "https://feeds.bbci.co.uk/ukrainian/rss.xml", "Eurasie", "Sécurité", "uk"),

    # ================================================================== ARABE
    ("BBC Arabe", "https://feeds.bbci.co.uk/arabic/rss.xml", "Moyen-Orient", "Diplomatie", "ar"),
    ("DW Arabe", "https://rss.dw.com/rdf/rss-ar-all", "Moyen-Orient", "Diplomatie", "ar"),
    ("RFI Arabe", "https://www.rfi.fr/ar/rss", "Moyen-Orient", "Diplomatie", "ar"),
    ("Al Jazeera (arabe)", "https://www.aljazeera.net/xml/rss/all.xml", "Moyen-Orient", "Politique intérieure", "ar"),
    ("Anadolu Agency (arabe)", "https://www.aa.com.tr/ar/rss/default?cat=guncel", "Moyen-Orient", "Politique intérieure", "ar"),
    ("RT (arabe)", "https://arabic.rt.com/rss/", "Moyen-Orient", "Politique intérieure", "ar"),

    # ================================================================== PERSAN / TURC / KURDE
    ("BBC Persan (Iran/Afghanistan)", "https://feeds.bbci.co.uk/persian/rss.xml", "Moyen-Orient", "Sécurité", "fa"),
    ("BBC Turc", "https://feeds.bbci.co.uk/turkce/rss.xml", "Moyen-Orient", "Diplomatie", "tr"),
    ("BBC Pashto (Afghanistan)", "https://feeds.bbci.co.uk/pashto/rss.xml", "Asie", "Sécurité", "ps"),
    ("Anadolu Agency (turc)", "https://www.aa.com.tr/tr/rss/default?cat=guncel", "Moyen-Orient", "Politique intérieure", "tr"),

    # ================================================================== CHINOIS / JAPONAIS / CORÉEN
    ("BBC Chinois (simplifié)", "https://feeds.bbci.co.uk/zhongwen/simp/rss.xml", "Asie", "Politique intérieure", "zh"),
    ("BBC Japonais", "https://feeds.bbci.co.uk/japanese/rss.xml", "Asie", "Politique intérieure", "ja"),
    ("BBC Coréen", "https://feeds.bbci.co.uk/korean/rss.xml", "Asie", "Sécurité", "ko"),

    # ================================================================== ASIE DU SUD / SUD-EST
    ("BBC Hindi (Inde)", "https://feeds.bbci.co.uk/hindi/rss.xml", "Asie", "Politique intérieure", "hi"),
    ("BBC Ourdou (Pakistan)", "https://feeds.bbci.co.uk/urdu/rss.xml", "Asie", "Sécurité", "ur"),
    ("BBC Bengali", "https://feeds.bbci.co.uk/bengali/rss.xml", "Asie", "Politique intérieure", "bn"),
    ("BBC Indonésien", "https://feeds.bbci.co.uk/indonesia/rss.xml", "Asie", "Politique intérieure", "id"),
    ("BBC Vietnamien", "https://feeds.bbci.co.uk/vietnamese/rss.xml", "Asie", "Politique intérieure", "vi"),
    ("BBC Thaï", "https://feeds.bbci.co.uk/thai/rss.xml", "Asie", "Politique intérieure", "th"),
    ("BBC Birman (Myanmar)", "https://feeds.bbci.co.uk/burmese/rss.xml", "Asie", "Sécurité", "my"),

    # ================================================================== AFRIQUE (langues locales)
    ("BBC Swahili", "https://feeds.bbci.co.uk/swahili/rss.xml", "Afrique", "Politique intérieure", "sw"),
    ("BBC Hausa (Nigeria/Sahel)", "https://feeds.bbci.co.uk/hausa/rss.xml", "Afrique", "Sécurité", "ha"),
    ("BBC Amharique (Éthiopie)", "https://feeds.bbci.co.uk/amharic/rss.xml", "Afrique", "Politique intérieure", "am"),
    ("BBC Somali", "https://feeds.bbci.co.uk/somali/rss.xml", "Afrique", "Sécurité", "so"),

    # ================================================================== EURASIE CENTRALE
    ("BBC Azéri", "https://feeds.bbci.co.uk/azeri/rss.xml", "Eurasie", "Politique intérieure", "az"),
    ("BBC Ouzbek", "https://feeds.bbci.co.uk/uzbek/rss.xml", "Eurasie", "Politique intérieure", "uz"),
    ("BBC Kirghize", "https://feeds.bbci.co.uk/kyrgyz/rss.xml", "Eurasie", "Politique intérieure", "ky"),

    # ================================================================== CYBER / INGÉRENCE (Europe)
    ("EU DisinfoLab", "https://www.disinfo.eu/feed/", "Europe", "Ingérences étrangères", "en"),
    ("EUvsDisinfo", "https://euvsdisinfo.eu/feed/", "Europe", "Ingérences étrangères", "en"),
    ("Vigilance Bulletins CERT-FR", "https://www.cert.ssi.gouv.fr/feed/", "Europe", "Cybersécurité", "fr"),
]
