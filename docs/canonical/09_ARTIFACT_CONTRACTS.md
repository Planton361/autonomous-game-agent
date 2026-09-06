# Artefaktverträge und Annahmekriterien

**Version:** 1.0 · **Release:** ALIGN-2026-09-06-v1.0  
Dieses Dokument beauftragt noch keine Forschungsergebnisse. Es legt fest, wie Fachchats künftig **genau ein** Artefakt bearbeiten.

## 1. Gemeinsamer Vertrag

Jeder Auftrag referenziert SOT-Version, Quellenstände, gegebenenfalls Commit und Daten-/Protokollversion. Er benennt Audience, genau ein Zielartefakt, Masterformat, erlaubte Derivate, Scope und Non-goals, Annahmekriterien und Rückgabe.

Ein Artefakt braucht einen eindeutigen Status: Entwurf, fachlich geprüft, für Betreuungsabstimmung freigegeben, präregistriert, empirisch ausgewertet oder eingereicht. Kein Status wird aus Dateiname, Länge oder Layout abgeleitet. Primärquellen oder Daten müssen die tragenden Aussagen tatsächlich stützen.

Der Fachchat liefert: Artefakt + Quellen-/Claim-Mapping + Änderungen + Grenzen + Übergabe. Eine Quellenliste ohne Claimbezug reicht für zentrale Neuheits- und Ergebnisbehauptungen nicht. Ein Screenshot einer Tabelle ist kein Ersatz für ihre zugrunde liegende Datendatei.

Ein Ergebnistext wird nicht parallel in Markdown, DOCX und LaTeX redaktionell weitergeführt. Der Auftrag erklärt einen Master; weitere Formate sind versionierte Exporte. Vorherige Fassungen bleiben archiviert.

## 2. GAP-001 – fokussierte Gap-Analyse

**Zweck:** Prüfen, was zu A/B bereits beantwortet wurde, welche Methoden übernommen werden können und welcher konkrete Erkenntnisgewinn offenbleibt.

**Quellen:** SOT; neuester Plan; altes Literatur-/Quellenregister als Leads; aktuelle Primärliteratur. Frühere Chatcites sind keine neue Verifikation.

**Pflichtinhalt:**

- Suchdatum, Suchräume/Begriffe, Ein-/Ausschlusskriterien und Grenzen der Abdeckung.
- Je Arbeit Titel, Autoren, Version/Datum, Venue-/Preprintstatus, dauerhafte URL/DOI, Prüftiefe und konkrete Fundstellen.
- Tatsächlicher Ansatz: Modelltraining vs. Prompting; Observation/Action/Memory; Datenherkunft; Belohnung; Tasks; Budgets; verglichene Bedingungen.
- Getrennte Spalten: Befund der Autoren, explizite Limitation/Future Work, eigene Abgrenzungsinferenz, nutzbare Übernahme.
- Direkte Konkurrenz zu Persona-Erfahrungspfaden, Cross-Run-Synthese, spontanem Erinnern, propositionalem/präskriptivem Wissen und ihrer Kopplung.
- Je Gap-Kandidat: exakter Claim, engster Vergleich, warum nicht nur neues Spiel, denkbarer falsifizierbarer Test, Ressourcenrisiko und Status.
- Auch **gegen** die erhoffte Neuheit gerichtete Quellen. Keine numerischen „Gap-Sicherheitswerte“ ohne fundiertes Messmodell.

**Annahme:** Zentrale Neuheitsclaims lassen sich auf geprüfte Methoden-/Ergebnispassagen zurückführen. „Nicht gefunden“ ist nicht „existiert nicht“. Codeverfügbarkeit ist nicht Replizierbarkeit; Ressourcen-/Lizenzprüfung nur behaupten, wenn durchgeführt.

**Nicht:** neue Forschungsrichtung beschließen, Manuskripte vollständig schreiben oder neue Quellenlisten ungeprüft als Wahrheit veröffentlichen.

## 3. EXPOSE-001 – Exposé zur Betreuung

**Zweck:** Einen begrenzten, relevanten und machbaren Promotionsentwurf vorstellen.

**Pflichtinhalt:** Problem, Motivation und Anwendungsbezug; A/B und Verbindung; präziser Gap-Status; Fragestellungen; erster aussagekräftiger Vergleich; vorhandene versus geplante Infrastruktur; Messung/Validität; Ressourcen; Risiken; gestufter Publikationsbogen; offene institutionelle Fragen.

**Quellen:** freigegebene SOT, aktuelle Gap-Karten, T0-/S0-Ergebnis und gegebenenfalls Technical Report; konkrete Promotions-/Betreuerquellen nach aktueller Prüfung.

**Annahme:** Ein Betreuer erkennt, was untersucht wird, welche konkurrierenden Lösungen existieren, welche Evidenz schon da ist und was als Erstes getestet wird. Ein methodischer Kandidat wird nicht als fertiger Beitrag verkauft. Wirtschaftlicher Transfer wird begründet und als noch zu prüfend bezeichnet. Keine AGI- oder Bewusstseinsclaims.

**Nicht:** eine Dissertation auf Vorrat schreiben, fest drei Pflichtpublikationen oder Betreuungszusage behaupten, unbekannte Hardwareleistung erfinden, fehlende Daten durch plausible Zahlen ersetzen.

**Umfang:** nach Zweck/Audience und gültiger Anforderung festlegen. Frühere 8–12 Seiten sind Planungshinweis, keine normative Mindestzahl. Ein Kurzexposé ist ein eigener späterer Auftrag oder ausdrücklich deklarierter Export, keine automatisch zweite Textbaustelle.

## 4. TECHREPORT-001 – technischer Forschungsapparat

**Zweck:** Reproduzierbar dokumentieren, was der Agent am geprüften Stand tatsächlich kann und welche Grenzen gelten.

**Pflichtinhalt:** Commit/Tree/Dirty-Status; Entry Points und Datenfluss; Contracts; Run-Modi; Capture/Bridge/Perception; Cortex/Manager/Body; Memory; Verifier und Input-Safety; konkrete Tests; bekannte Grenzen; Bedien-/Reproduktionsschritte ohne Spoiler.

**Statusmatrix:** design-spezifiziert, implementiert, technisch getestet, integriert, messvalidiert, in echter Umgebung gezeigt und vergleichend evaluiert getrennt führen. Bei fehlender Evidenz „nicht belegt“ statt „funktioniert“.

**Annahme:** TECH-ORCH prüft Code-/Testclaims. Jeder zentrale Capability-Claim hat Beleg und begrenzten Geltungsbereich. Keine Übernahme alter Testzahlen oder Head-SHAs als Gegenwart ohne erneute Prüfung. Kein Gameplay-Tutorial.

**Nicht:** Primärpublikationsneuheit erfinden, wissenschaftliche Ergebnisse aus Unit Tests ableiten, nebenbei Architektur ändern. Der Bericht ist nicht bloß ein umbenanntes altes Working Paper.

## 5. PROTOCOL-001 – Mess- und Studienprotokoll

**Zweck:** Einen konkreten Vergleich vor seiner bestätigenden Durchführung interpretierbar machen.

**Pflichtinhalt:** RQ/Estimand, Treatment, Vergleich, Population/Aufgaben, erlaubte Evidenz, fixe und veränderliche Komponenten, Auftrags-/Linien-/Run-Definition, Budget, Hauptendpunkt, sekundäre Diagnosen, Zuweisung/Randomisierung, Pilot-/Holdout-Splits, Stichproben-/Präzisionsplanung, Missingness/Refusals/Integritätsfälle, Analyse und Sensitivitätsgrenzen.

A: Persona versus Modellvergleich versus Historienwirkung getrennt; Promptparaphrasen, Framing und gegebenenfalls neutraler Memory-Schreiber. Verhaltensraten benötigen wohldefinierte Gelegenheiten, nicht nur rohe Zählwerte.

B: gemeinsame Erfahrung versus eigener Closed Loop; explizite Fusionsprobe versus spontane Nutzung; alternative hinreichende Evidenz, Provenienz, Kosten der Konsolidierung und Lookup.

**Annahme:** TECH-ORCH bestätigt, welche benötigten Felder/Outcomes tatsächlich bereitgestellt werden können. Schätzgröße und Datenfluss passen zusammen. Nicht implementierte Messung bleibt geplant. Keine beliebige Linienzahl oder einfache Prozentzerlegung als methodische Garantie.

**Nicht:** Hidden-State-Ausnahmen eigenmächtig freigeben; Regel „run“ automatisch auf vererbtes Memory übertragen; Agententod ohne Prüfung als unabhängige Zensierung behandeln.

## 6. PAPER-A-001 – Instruktionen und Erfahrungsgewinn

**Arbeitsfokus:** Unmittelbare Wirkung von Modell-/Instruktionskonfiguration und gegebenenfalls Persistenz über unterschiedlich erworbene Historien. Ein bloßes Ranking oder „explorativ prompten → mehr Exploration“ ist kein ausreichender Beitrag.

**Benötigt:** konkrete Gap-Karte, freigegebenes Protokoll, Quellenbelege, Daten-/Analysestand. Ohne Daten nur Introduction/Related Work/Methods/Skeleton; Results bleiben ausdrücklich offen.

**Annahme:** Claims unterscheiden beobachtete Konfigurationseffekte, randomisierte Promptwirkung und kontrollierte Historienintervention. Fehler/Refusals/Kosten und Framing nicht verschweigen. Keine psychologischen Zuschreibungen ohne passende Operationalisierung.

## 7. PAPER-B-001 – episodische Evidenz zu späterer Handlung

**Arbeitsfokus:** Selbstständige Kombination eigener verteilten Erfahrungen und späterer Entscheidungsnutzen. Nicht nur Retrieval-Recall oder Syntheseprosa.

**Benötigt:** starke Baseline, eindeutig dokumentierte Anpassungen veröffentlichter Verfahren, vergleichbare Ressourcen, fester Body, eindeutige Test-/Erwerbstrennung und Daten-/Analysestand.

**Annahme:** Episode, Abstraktion, bedingte Regel und Plan getrennt; keine künstliche Evidenzvermehrung; keine Claim-Fusion nur wegen korrekter Quellen-IDs. Gemeinsame Erfahrung und eigener Closed Loop werden korrekt getrennt berichtet.

## 8. PAPER-C-001 – Kopplung, Persistenz oder Transfer

**Arbeitsfokus:** Eine konkrete Anschlussfrage über instruktionsabhängig erworbene Erfahrung und ihre weitere Nutzung/Reichweite, nicht bloß die Zusammenfassung von A und B.

**Benötigt:** hinreichend stabile A/B-Ergebnisse oder klar definiertes Alternativeset. Kompatible Welt-/Memory-Bezüge. Klare Festlegung, ob Wissen, Lernverfahren oder motorische Skills transferiert werden.

**Annahme:** Ein Historienaustausch wird nicht als vollständige natürliche Mediation verkauft. Kein wirtschaftlicher Nutzen nur aus Game-Erfolg. Ein gleich aussehender Test unter anderem Namen ist kein neues unabhängiges Paper.

## 9. REVIEW-001 – unabhängige Gegenprüfung

**Zweck:** Ein eingefrorenes Artefakt anhand seines Auftrags, der SOT und der Belege prüfen.

**Pflicht:** Findings nach Schweregrad, genaue Fundstelle, Quelle/Begründung, Auswirkung und minimaler Korrekturvorschlag. Prüfen: Quelle trägt Claim? RQ passt Treatment? Endpunkt passt Claim? Current HEAD wirklich geprüft? Modus-/Datenleak? Ergebnis oder Hypothese? Eigene Erhebung oder Literatur? Zeitgebundene Angaben aktuell?

**Nicht:** den gesamten Text neu schreiben, heimlich neue Literaturclaims einbauen oder selbst eine Revision freigeben, die nicht geprüft wurde.

## 10. Prioritäten und Abhängigkeiten

T0 und S0 zuerst parallel. Danach kleinster zulässiger Pilot-Schritt und GAP-001. Exposé darf als ehrlicher Plan entstehen, bevor empirische Ergebnisse vorliegen; seine Gap-Behauptungen brauchen jedoch klaren Status. Technical Report hängt von geprüften Implementierungsbelegen ab. Das konkrete Messprotokoll muss vor bestätigenden Runs feststehen. Ergebnis-Papers hängen von tatsächlich durchgeführten Analysen ab.

Zunächst höchstens zwei wissenschaftliche Aufträge parallel und nie dieselbe Quelldatei in zwei Chats. Mögliche Reihenfolge: GAP-001 → EXPOSE-001; parallel dazu TECHREPORT-001, sobald TECH-ORCH genügend Belege liefert. PROTOCOL-001 wird vor der Studie eingeschoben; Papers folgen ihrem Datenstand, nicht einer willkürlichen Deadline.

## 11. Versionsschema für Fachartefakte

Beispiel, als Konvention zu übernehmen: `GAP-001_v0.1.md`, `EXPOSE-001_v0.1.docx`, `TECHREPORT-001_<shortsha>_v0.1.md`, `PROTOCOL-001_v0.1.md`. Der Auftrag benennt den Master. Ein Releaseexport kann mehrere Formate enthalten, aber nur eine inhaltliche Revision.

Jede Datei nennt ID, Version, Status, Owner, SOT-Basis, Quellen-/Datenstand, Changelog und bekannte Grenzen. Nur der zuständige Orchestrator markiert eine aktive Kandidatenversion; Anton entscheidet externe Freigabe.
