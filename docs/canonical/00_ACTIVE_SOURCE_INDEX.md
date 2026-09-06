# Aktiver Quellenindex und Leseregeln

**Version:** 1.0 · 6. September 2026  
**Release:** ALIGN-2026-09-06-v1.0  
**Funktion:** Einstieg für alle neuen Chats. Ergänzt den eingefrorenen Baseline-Index; überschreibt dessen historischen Text nicht.

## 1. Zuerst lesen

1. `07_RESEARCH_PROGRAM_SOT.md`: ausgewähltes Forschungsprogramm, Grenzen, Begriffe.
2. `08_ORCHESTRATION_PROTOCOL.md`: Zuständigkeiten, Delegation, Übergaben und Änderungsrecht.
3. `10_ORCHESTRATOR_MANDATES.md`: eigener Rollenauftrag und erster Review.
4. `09_ARTIFACT_CONTRACTS.md`: nur für das jeweilige Ergebnis relevante Abschnitte.
5. `02_ARCHITECTURE_CANONICAL.md` und `04_RESEARCH_PROTOCOL_CANONICAL.md`: technische und experimentelle Invarianten.
6. Auftragsbezogene Baseline-Quellen, Primärliteratur und GitHub-Belege.

Dateinamenszusätze wie `(1)` ändern die inhaltliche Quelle nicht. Version, Titel und bei Zweifeln Hash prüfen. Ist eine erforderliche Quelle nicht zugänglich, die Lücke nennen und keine angenommene vollständige Kenntnis behaupten. Nicht den gesamten Ursprungschat rekonstruieren; dieses Paket ist sein strukturierter Übergabestand.

## 2. Welche Quelle beantwortet welche Frage?

| Aussage | Maßgebliche Quelle |
| --- | --- |
| Was ist implementiert? | Aktuell gelesener GitHub-HEAD, Code, Integration und tatsächliche Prüfbelege |
| Was wurde getestet? | Konkreter PR-/CI-/Testbericht mit Commit, Datum und Umfang; eine Workflowdatei ist noch kein bestandenes Ergebnis |
| Welche Arbeit ist aktiv? | Aktives GitHub-Issue / erteilter Artefaktauftrag; lokale Änderungen nur als lokale Änderungen |
| Welche Forschung wollen wir? | Explizite Nutzerentscheidung, dauerhaft festgehalten in `07_RESEARCH_PROGRAM_SOT.md` beziehungsweise freigegebenem Nachtrag |
| Welche Architektur- und Integritätsgrenzen gelten? | Kanonische Architektur/Protokoll; keine automatische Lockerung durch ein Paper oder Review |
| Wer darf was bearbeiten? | `08_ORCHESTRATION_PROTOCOL.md`, Rollenmandat und konkreter Auftrag |
| Wo steht die technische Phase? | GitHub-Milestone/Issues und bestätigtes Exit-Gate; Project als operative Sicht |
| Was sagt die Literatur? | Geprüfte Primärquelle, Version und exakte Fundstelle; Gap-Matrix ist Navigationshilfe |
| Welche Ergebnisse gibt es? | Tatsächliche Daten, eingefrorenes Protokoll, Analyse und Outcome-Audit |
| Welche wissenschaftlichen Behauptungen sind verwendbar? | Claim-Evidence-Register mit Quellenprüfung und Freigabestatus |
| Welcher Draft ist aktuell? | Vom Scientific Orchestrator geführtes Artefaktregister mit genauem Pfad und Version |

GitHub ist nicht die Wahrheit über eine Forschungslücke; ein Canonical-Plan ist nicht die Wahrheit über laufende Implementierung. Ein Ergebnis aus einem anderen Chat wird erst übernommen, nachdem der Empfänger das Übergabepaket gelesen hat.

## 3. Aktive gemeinsame Quellen

| Quelle | Status und Verwendung |
| --- | --- |
| `00_ACTIVE_SOURCE_INDEX.md` | Aktiver Einstieg und Konfliktregeln |
| `01_PROJECT_CHARTER.md` | Eingefrorene Vision; aktuelle Schwerpunktsetzung aus 07 lesen |
| `02_ARCHITECTURE_CANONICAL.md` | Normative Zielhierarchie; keine Implementierungsbehauptung |
| `03_RESEARCH_ROADMAP_CANONICAL.md` | Eingefrorene Capability-Reihenfolge und Gates; nicht aktuelle Issue-Liste und nicht zwingende Dissertationsgliederung |
| `04_RESEARCH_PROTOCOL_CANONICAL.md` | Geltende No-Spoiler-, Modus-, Daten- und Sicherheitsgrenzen |
| `05_LITERATURE_BASELINE_2026-09-01.md` | Historischer Recherche-Snapshot, nicht gegenwärtig vollständige Forschung |
| `06_REFERENCES_AUTONOMOUS_GAME_AGENTS.bib` | Zugehörige historische Bibliografie, keine ungeprüfte aktuelle Referenzdatenbank |
| `07_RESEARCH_PROGRAM_SOT.md` | Aktuelle gemeinsame Forschungsgrundlage aus dem Nutzerauftrag |
| `08_ORCHESTRATION_PROTOCOL.md` | Arbeitsteilung und Freigabeprozess |
| `09_ARTIFACT_CONTRACTS.md` | Auftragstypen, Nachweise, Qualitäts- und Übergabekriterien |
| `10_ORCHESTRATOR_MANDATES.md` | Zwei Orchestratoren und erster begrenzter Prüfauftrag |

Der alte `00_CANONICAL_SOURCE_INDEX.md` bleibt als Baseline archiviert und wird im Repository nicht durch eine anders benannte Datei heimlich entfernt. Ein späterer Docs-PR ergänzt dort einen klaren Verweis auf diesen aktiven Index.

## 4. Bekannte Spannungen – explizite Auflösung und offene Reviews

| Frühere Quelle / Aussage | Aktuelle Lesart | Darf ein Chat eigenmächtig ändern? |
| --- | --- | --- |
| Charter stellt Body-Lernen/Transfer stark heraus | Langfristige Optionen; A/B sind aktuelle Kernstränge | Schwerpunkt nicht ohne Nutzerentscheid wechseln |
| Canonical Roadmap A–N | Capability-Plan; nicht drei Pflichtpapers und keine Pflicht, alle späten Phasen vor Studie A/B abzuarbeiten | Operative Repriorisierung vorschlagen; Gate-Änderungen brauchen Review und Freigabe |
| Working Paper v2 RQ1/RQ2 | Historisches Studiendesign | Nicht umnummerieren oder rückwirkend als neues Programm ausgeben |
| Ältere „Forschungspfade“-Datei priorisiert nur F1 | Durch die spätere Auswahl zweier Stränge A/B als aktuelle Priorisierung abgelöst | Historie behalten; nicht als gleichrangige aktuelle Weisung lesen |
| Alter Plan sagt „D6 jetzt ausführen“ | Neuester Nutzerauftrag schaltet T0-Alignment-Review davor | Review durchführen; D6 nicht still fortsetzen |
| Run als primäre Einheit im Pilotprotokoll | Für persistent lernende Sequenzen müssen Linien/Cluster im neuen Studienaddendum ausdrücklich behandelt werden | Addendum erstellen/reviewen, keinen Kanon still umschreiben |
| Öffentliche API-Modelle als Vergleichswunsch | Explorative Kohorte zulässig; keine automatische offizielle Offline-Eligibility | Eigene Studienregel beantragen |
| Evaluator-only Hidden State in fremden Benchmarks | Kein Freibrief für Hidden State in offiziellen Pilotläufen | Separates Protokoll und explizite Freigabe nötig |
| „Lernen nur zwischen Runs“ in Engineering-Kurztexten | Gewichtsupdates nur zwischen Runs; erlaubter Wissenszustand kann während Runs wachsen | Unklarheit im T0-Review auflösen, keine In-Run-Gewichtsänderung einführen |

Diese Präzisierungen dokumentieren den aktuellen Nutzerwillen. Noch nicht entschiedene Protokoll- oder Roadmapänderungen bleiben offen und werden nicht durch Interpretation aktiviert.

## 5. Historische und ergänzende Quellen

Das bisherige Working Paper v2, ältere Optionenmatrizen und Forschungsprogramme werden als Vorarbeit bewahrt. Der Forschungsplan und das Kurzexposé vom 6. September sind der aktuell passende **Entwurf**, aber keine endgültig angenommene Gap-Analyse oder Präregistrierung. Das bibliografische Register daraus dient als Rechercheeingang und wird überprüft.

Nicht in die dauerhaften Projektquellen hochladen: ständig wechselnde Testzahlen, komplette pro-PR-Berichte, unstrukturierte Tageslogs und jedes konkurrierende Draft. Sie gehören in GitHub beziehungsweise in das jeweils konkrete Chat-Übergabepaket. Es gibt pro Artefakt genau eine aktive Version.

## 6. Aktivierung und Versionierung

Dieses Release wird zunächst durch Upload der fünf neuen gemeinsamen Quellen und Einsetzen der gemeinsamen Projektinstruktion aktiviert. Danach starten die beiden Orchestratoren. Die dauerhafte Übernahme ins Repository erfolgt als separater Dokumentations-PR mit Nutzer-Merge.

Projektuploads sind versionierte Lesekopien, kein automatisch synchronisiertes Dateisystem. Nach einer freigegebenen Änderung werden Repo-Version, Upload und beide Orchestratoren über ein Release-Delta aktualisiert. Ist eine Kopie älter, wird die Differenz zuerst gelesen; keine Quelle überschreibt still die andere.

Die Orchestratoren nennen beim Start ihre gelesene SOT-Version. Das schafft kontrollierte Referenzen, keine Garantie perfekter Chat-Erinnerung.
