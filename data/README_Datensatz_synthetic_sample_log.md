# Crawler-Monitor – Beispiel-Datensatz für GLAMhack 2026

## Änderungshinweis (14. Nov 2026)

Ein Generierungsfehler wurde behoben: die sechs deklarierten KI-Bots
(GPTBot, ClaudeBot, Bytespider, CCBot, Amazonbot, PerplexityBot) teilten
sich versehentlich denselben 6er-IP-Block, der zudem in den IP-Bereich des
undeklarierten Crawlers fiel. Jeder Bot hat jetzt einen eigenen,
nicht überlappenden IP-Block in 198.51.100.0/24. Das Datenset enthält
dadurch jetzt 157 statt 121 eindeutige IP-Adressen; alle anderen Zahlen
(Zeilenanzahl, Zeitfenster, Verkehrstypen) sind unverändert.

## Was das ist

`crawler_monitor_sample_logs.csv` ist ein **synthetisches** (also erfundenes,
nicht aus dem IRF stammendes) Beispiel eines Web-Zugriffsprotokolls, wie es
typischerweise bei einem institutionellen Repositorium anfällt. Es wurde so
gebaut, dass es die in der Recherche dokumentierten echten Verhaltensmuster
nachbildet (u. a. aus dem UNC-Chapel-Hill-Bericht, dem COAR-Survey und dem
GLAM-E-Lab-Survey) – Teams können damit sofort arbeiten, unabhängig davon,
ob/wann ihr echte, freigegebene IRF-Logs liefern könnt.

Alle IP-Adressen stammen bewusst aus den für Dokumentationszwecke
reservierten Testnetzen (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24,
RFC 5737) – es sind garantiert keine echten Adressen.

## Die zwei Dateien

- **`crawler_monitor_sample_logs.csv`** – das, was die Hackathon-Teams bekommen.
  Enthält nur die "rohen" Zugriffsdaten, **keine** Information darüber, was
  Mensch, Bot oder aggressiver Crawler ist. Genau das sollen die Teams selbst
  herausfinden.
- **`crawler_monitor_ground_truth.csv`** – **nur für euch als Organisatorinnen**,
  nicht an die Teams weitergeben. Enthält pro Zeile, welchem der vier
  simulierten Verkehrstypen sie zugeordnet wurde, plus eine kurze Begründung.
  Nützlich, um am Ende zu beurteilen, wie gut die Prototypen der Teams die
  Realität tatsächlich treffen (eine Art "Lösung" zum Abgleichen).

## Spalten (Teams-Datei)

| Spalte | Bedeutung |
|---|---|
| `row_id` | laufende Nummer |
| `timestamp` | Zeitpunkt der Anfrage |
| `ip` | (fiktive) IP-Adresse |
| `method` | HTTP-Methode (hier immer GET) |
| `path` | aufgerufene URL/Pfad |
| `status` | HTTP-Statuscode der Antwort |
| `bytes_sent` | übertragene Datenmenge |
| `user_agent` | der "User-Agent"-String, mit dem sich der Client identifiziert (oder eben nicht ehrlich identifiziert) |
| `referrer` | von welcher Seite der Zugriff kam (falls angegeben) |

## Welche vier "Geschichten" in den Daten stecken

1. **Menschlicher Grundverkehr** (ca. 2'600 Zeilen) – normale Browser, über die ganze
   Periode (1.–14. Oktober 2026) verteilt, moderate Mengen.
2. **Legitime Suchmaschinen-Bots** (Googlebot, Bingbot; ca. 830 Zeilen) – crawlen
   stetig und mässig, holen artig `/robots.txt` ab.
3. **Deklarierte KI-Trainings-Bots** (GPTBot, ClaudeBot, CCBot, Bytespider,
   Amazonbot, PerplexityBot; ca. 5'370 Zeilen) – geben sich im User-Agent
   ehrlich zu erkennen, sind aber deutlich aggressiver als Suchmaschinen,
   besonders am 10./11. Oktober (der simulierte "Spike").
4. **Undeklarierter, aggressiver Crawler** (ca. 5'800 Zeilen) – der eigentliche
   Clou: Dieser gibt sich per User-Agent als ganz normaler Chrome-Browser aus.
   Erkennbar ist er **nur am Verhalten**: extrem viele Suchanfragen mit 15–25
   Filtern/Facetten gleichzeitig (das "Facetten-Flut"-Muster aus dem
   UNC-Chapel-Hill-Bericht), kein Referrer, aus über 80 verschiedenen
   IP-Adressen, fast ausschliesslich konzentriert auf den 10./11. Oktober.

Das ist absichtlich so gebaut: Eine reine User-Agent-Filterung (Typ 4 wird
dabei NICHT erkannt) reicht nicht – ein gutes Prototyp sollte zusätzlich
Verhaltensmuster erkennen. Das ist genau die Lücke, die echte Repositorien
laut den Studien aktuell haben.

## "Referenzlisten" – was damit gemeint ist

Das sind von der Community öffentlich gepflegte Listen bekannter Bot-Namen
bzw. User-Agent-Strings, die man benutzen kann, um Zugriffe automatisch
zuzuordnen, ohne die Namen jedes Bots selbst recherchieren zu müssen. Zwei,
die direkt zum Thema passen:

- **ai.robots.txt** (github.com/ai-robots-txt/ai.robots.txt) – von Freiwilligen
  gepflegte Liste bekannter KI-Crawler (GPTBot, ClaudeBot, Bytespider, CCBot,
  usw.) inkl. fertigem robots.txt zum Blockieren. Genau die Namen, die auch im
  Beispiel-Datensatz unter Typ 3 vorkommen.
- **COUNTER's Bot-Repository** (countermetrics.org/counter-bots) – die Liste, die
  Bibliotheken/Repositorien nutzen, um Bot-Zugriffe aus offiziellen
  Nutzungsstatistiken herauszurechnen (inzwischen inkl. der ai.robots.txt-Liste).

Für die Teams heisst das konkret: Sie müssen nicht selbst wissen, wie GPTBot
oder ClaudeBot heissen – sie können diese Listen laden und den `user_agent`
in den Logs automatisch dagegen abgleichen. Das deckt aber nur Typ 3 ab –
Typ 4 (undeklariert) bleibt die eigentliche Herausforderung der Challenge.

## Woher die Zahlen/Muster stammen

Die Verhaltensmuster (Facetten-Flut, IP-Rotation, Ignorieren von robots.txt,
Bursts) sind nicht erfunden, sondern aus dem öffentlich dokumentierten Fall
von UNC Chapel Hill Libraries übernommen (Mitigating Aggressive Crawler
Traffic in the Age of Generative AI, Code4Lib Journal). Die konkreten
Zahlenwerte und Zeilen selbst sind erfunden/synthetisch.
