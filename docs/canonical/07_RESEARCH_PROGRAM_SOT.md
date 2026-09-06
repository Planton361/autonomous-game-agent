# Forschungsprogramm – gemeinsame Source of Truth

**Dokument-ID:** SOT-001  
**Version:** 1.0 · 6. September 2026  
**Alignment-Release:** ALIGN-2026-09-06-v1.0  
**Projekt:** `Planton361/autonomous-game-agent`  
**Fachlicher Entscheider:** Anton  
**Status:** Aus dem expliziten Nutzerauftrag erstellte gemeinsame Arbeitsgrundlage. Ihre Aufnahme in Projektquellen und Repository ist ein gesonderter Aktivierungsschritt. Keine Präregistrierung, kein Neuheitsnachweis, kein Bericht empirischer Ergebnisse.

## 1. Zweck und Reichweite

Dieses Dokument erhält die im Ursprungschat ausgewählte Forschungsrichtung und begrenzt die Arbeit aller Folgechats. Es ist die gemeinsame normative Referenz für Forschungsfokus, Begriffe, Nichtziele und Übergänge zwischen wissenschaftlicher und technischer Arbeit. Es ist **kein** Live-Fortschrittsbericht und **keine** Wiederholung sämtlicher früher diskutierter Ideen.

Eine Source of Truth ist nicht die Behauptung, dass alles hier wahr, umgesetzt oder bewiesen ist. Sie legt fest, **welche Entscheidungen gelten und welchen epistemischen Status Aussagen besitzen**. Für Implementierung ist weiterhin GitHub HEAD maßgeblich; für aktuelle Aufträge das aktive Issue beziehungsweise der erteilte Artefaktauftrag; für Ergebnisse deren tatsächliche Daten und Prüfberichte.

Der Nutzer hat zwei Forschungsstränge ausdrücklich ausgewählt. Frühere Richtungen wie Mind-vs.-Body-Anteilszerlegung, offene Skill-Discovery oder ein eigener Benchmark sind dadurch nicht zu gleichrangigen Pflichtprojekten geworden. Die Forschungsfrage wird nicht bei jedem neuen Paper ausgetauscht. Ein ernsthafter Gegenbefund wird jedoch nicht ignoriert: Er löst einen dokumentierten Änderungsantrag aus.

## 2. Ursprüngliche Motivation – was erhalten bleiben muss

Der Ausgangspunkt ist die Frage, ob ein künstlicher Agent ein anspruchsvolles RPG durch eigene Erfahrung zunehmend besser bewältigen und schließlich ein langfristiges externes Ziel erreichen kann. Interessant ist nicht nur eine erfolgreiche Aktionsfolge, sondern die Entwicklung: erkunden, Beobachtungen sammeln, Zusammenhänge vermuten, bisher getrennte Erfahrungen verbinden, Erwartungen bilden und später anders handeln.

Fear & Hunger ist der motivierende Entwicklungspilot. Seine Story oder konkreten Lösungen sind nicht der Forschungsgegenstand. Der spätere wissenschaftliche Nachweis darf eine geeignete andere Umgebung verwenden. Ein vollständiges Ending ist ein technisches Leitresultat, aber keine notwendige Voraussetzung jeder wissenschaftlichen Aussage.

Jeder Run ist ein ernsthafter Missionsversuch. Informationssuche und Lernen sind Mittel zur Zielverfolgung. Kein verpflichtendes Gameplay nur zum Maximieren von Trainingsreward, Skill-Anzahl oder Neuheit. Tod bleibt ein gescheiterter Versuch mit möglicherweise nutzbarer Erfahrung, nicht automatisch ein erfolgreicher Lernschritt und keine automatisch bekannte Ursache.

Die menschliche Analogie motiviert das Projekt, rechtfertigt aber keine Behauptung über Gefühle, Bewusstsein, menschliche Persönlichkeit oder lesbare innere Gedanken.

## 3. Gemeinsame wissenschaftliche Klammer

**Arbeitsfrage:** Wie prägen Modellkonfiguration und Verhaltensinstruktion die eigene Erfahrungsgewinnung eines zielgerichteten LLM-Agenten, und wie wird diese Erfahrung über Episoden hinweg zu Wissen, das spätere Entscheidungen unterstützt?

**Arbeitsablauf, keine bereits nachgewiesene Kausalkette:**

`Modell + Instruktion → vorgeschlagene Ziele → autorisierte Ausführung → eigene Erfahrung → Memory / Synthese → späteres Verhalten`

**Arbeitstitel, nicht endgültig:**

*Behavioral Instructions and Cross-Episode Knowledge Synthesis in Goal-Directed LLM Agents*

Beide Stränge bleiben Teil des Vorhabens. Strang B kann den methodischen Kern liefern, Strang A einen eigenständigen empirischen Beitrag. Diese Rollen sind eine Planung, keine Wertung, dass A unwichtig wäre. Die Reihenfolge eines ersten bestätigenden Experiments hängt von Gap- und Machbarkeitsprüfung ab. Ein neutrales Einzelmodell ist für den technischen Pilot ausreichend, nicht für allgemeine vergleichende Befunde.

## 4. Strang A – Modelle, Persona-Instruktionen und Erfahrungserwerb

### A1. Ausgewähltes Interesse

Untersucht werden unterschiedliche Vorgehensweisen: Informationssuche, Exploration, Risikoentscheidungen, Wiederholung oder Abbruch von Ansätzen, Zielwechsel, Ressourcennutzung und spätere Entwicklung. Entscheidend ist die Wirkung auf tatsächlich gewonnene Erfahrungen, nicht nur Sprachstil.

### A2. Drei getrennte Vergleiche

1. **Modellvergleich:** Konkrete versionierte Cortex-Konfigurationen bei vergleichbarem Scaffold. Ein Unterschied ist ein Systemeindruck unter diesen Bedingungen; er isoliert nicht bestimmte Trainingsdaten oder eine angeborene Persönlichkeit.
2. **Persona-/Instruktionsintervention:** Innerhalb desselben Modells wird ausschließlich ein vorab festgelegter Verhaltensblock verändert. Mission, zulässige Evidenz, Safety, Body und Autorität bleiben gleich.
3. **Persistenz über Erfahrung:** Nach einem definierten Erfahrungserwerb wird unter vereinheitlichter aktueller Instruktion geprüft, ob unterschiedlich entstandene Historien spätere Entscheidungen beeinflussen.

Die Reihenfolge ist nicht unveränderlich. Kein Orchestrator darf aber die drei Vergleiche sprachlich oder analytisch gleichsetzen.

### A3. Enger Gap-Kandidat

Unter welchen Bedingungen wirkt eine anfängliche Verhaltensinstruktion über die selbst erzeugte Erfahrungsgeschichte auf spätere Zielverfolgung fort, auch wenn die aktuelle Instruktion standardisiert wird?

Das ist **zu prüfen**, nicht als „bisher unerforscht“ vorauszusetzen. Weder „Modelle handeln verschieden“ noch „Persönlichkeits-Prompts beeinflussen Risikowahl“ ist als ausreichende Neuheit reserviert.

### A4. Offene Designentscheidungen

Persona-Dimension, Modellzahl, Promptparaphrasen, Aufgaben, Hauptendpunkt, Erfassungsbudget und Memory-Schreiber sind noch nicht final festgelegt. Der erste Vergleich muss klein bleiben. Ein Prompt „exploriere häufiger“ plus häufigere Exploration belegt zunächst Instruktionsbefolgung. Narrative Rahmung, Parsing, Refusals, Latenz und unterschiedliche tatsächlich verfügbare Handlungsgelegenheiten sind alternative Erklärungen.

Persona darf keine harten Sicherheitsgrenzen verschieben. Protokolliert werden Cortex-Vorschlag, Manager-Annahme/Ablehnung und ausgeführte Handlung getrennt. Gleicher Body bedeutet nicht gleiche spätere Beobachtungen, wenn die Strategien unterschiedliche Wege erzeugen.

## 5. Strang B – aus Erfahrungen handlungsrelevantes Wissen synthetisieren

### B1. Ausgewähltes Interesse

Kann der Agent selbstständig erkennen, dass zeitlich oder episodisch getrennte Erfahrungen zusammengehören, gemeinsam eine neue Schlussfolgerung tragen und für ein späteres Ziel brauchbar werden?

Es geht nicht allein um Abruf ähnlicher Texte und nicht um künstlich eingeschleuste Falschinformationen. Der positive Lernprozess ist zentral. Unbegründete Fusion und Vergessen sind Diagnosefälle, nicht die Hauptidentität des Vorhabens.

### B2. Vier zu trennende Objekte

| Objekt | Inhalt | Nicht verwechseln mit |
| --- | --- | --- |
| Episode | Tatsächlich beobachteter Verlauf mit Aktion, Outcome und Provenienz | Allgemeinen Regeln |
| Abgeleitete Aussage / Hypothese | Beziehung zwischen einer oder mehreren Erfahrungen; Geltungsbereich und Evidenz | Einer neuen Rohbeobachtung |
| Bedingte Handlungsregel | Unter welchen beobachtbaren Bedingungen ein Ziel oder Vorgehen nützlich sein könnte | Ausführbarem Body-Code oder automatisch gültigem Contract |
| Aktueller Plan | Jetzt gewähltes, durch den Manager zu groundendes Ziel | Dauerhafter Wahrheit über das Spiel |

Die Begriffe können im Code anders heißen. Semantische Trennung und Herkunft dürfen dabei nicht verlorengehen. Ein Quellenverweis belegt Herkunft, nicht automatisch Wahrheit.

### B3. Synthese ohne erfundene Erfahrung

Eine Synthese erhält Ursprungs-/Elternreferenzen, Welt- und Run-Bezug, Geltungsbereich, Unsicherheitsstatus sowie gegebenenfalls Widersprüche. Eine aus drei Episoden abgeleitete Idee wird nicht als vierte beobachtete Episode gespeichert. Wiederholte Zusammenfassungen derselben Quelle sind keine unabhängige Evidenz.

Kompression darf Kontextkosten reduzieren. Sie verspricht weder monotone Qualitätssteigerung noch „Superinformation“. Relevante Bedingungen und Ausnahmen dürfen nicht still verloren gehen. Rohmaterial bleibt für Audit zugänglich, aber nicht unbeschränkt im Cortex-Kontext.

### B4. Enger Gap-Kandidat

Unter welchen Bedingungen kann ein Agent mehrere selbst gewonnene, über Episoden verteilte Evidenzfragmente **ohne expliziten Fusionshinweis** verbinden und ihre Synthese in einer späteren Handlung erfolgreich verwenden?

Getrennte Diagnosen: gespeichert → gefunden → gemeinsam im Kontext → abgeleitet → genutzt → externes Ergebnis. Jede Stufe kann funktionieren, während die nächste scheitert. Eine gute Antwort auf eine direkte Frage beweist noch keine spontane Nutzung während einer Mission.

### B5. Gestufte Untersuchung

Zuerst verarbeiten starke Vergleichsverfahren dieselben zulässigen Erfahrungsketten. Das isoliert deren Verarbeitung, ist aber kein Beweis autonomer Exploration. Danach folgt ein begrenzter Closed-Loop-Vergleich mit eigenen Erfahrungen pro Agentenlinie. Explizite Fusionsprobes bleiben gesonderte Diagnose und dürfen die Hauptläufe nicht primen.

Alternative hinreichende Evidenzketten müssen zugelassen werden. Das Entfernen einer einzigen Quelle ist bei redundanter Information kein abschließender Necessity-Test.

## 6. Verbindung A–B und spätere Reichweite

Die Kopplung untersucht, ob Unterschiede im Erfahrungserwerb durch unterschiedliche Verarbeitung fortbestehen, abgeschwächt oder verstärkt werden. Ein kontrollierter Austausch von Historien kann den Effekt bereitgestellter Historien schätzen. Er beweist keine vollständige natürliche Mediation aller ursprünglichen Persona-Effekte.

Historien müssen dieselbe Welt betreffen oder ausdrücklich zugelassene Übertragungsregeln erfüllen. Fremde Entity-IDs, nicht passende Regeln und in Memories enthaltene veraltete Body-Annahmen erzeugen keine sinnvollen Kreuzvergleiche.

Eine spätere anwendungsnahe Prüfung – etwa in einer isolierten IT-Support-/Diagnoseaufgabe – ist eine **Transferhypothese**. Erfolg im Spiel belegt keinen wirtschaftlichen Nutzen. Wissenstransfer, Transfer des Memory-Verfahrens und motorischer Skill-Transfer sind verschiedene Forschungsobjekte.

## 7. Gewählte Richtung, Vorschläge und offene Punkte

### Verbindlich aus dem Nutzerverlauf

- Erfahrung ist zentral: wie sie zustande kommt und wie sie spätere Zielverfolgung beeinflusst.
- A und B sind die ausgewählten Kernstränge; ihre Verbindung ist erwünscht.
- Technischer Pilot und wissenschaftliche Arbeit sollen getrennt orchestriert, aber gemeinsam ausgerichtet werden.
- Vor regulärer Fortsetzung der technischen Roadmap steht ein begrenzter Best-Practice-/Alignment-Review.
- Einzelne wissenschaftliche Artefakte werden an jeweils klar begrenzte Fachchats delegiert.
- GitHub/Codex ist der technische Lieferweg; keine unkoordinierte Umsetzung durch Schreibchats.
- Forschung soll nachvollziehbar sein und vor allem den nächsten Betreuungsmeilenstein ermöglichen.

### Forschungs- und Designvorschläge, noch zu prüfen

- Genaue Persona-Behandlung, Modelle, Memory-Methode und passende Baselines.
- Standardisierte neutrale spätere Evaluation und Verwendung eines neutralen Memory-Schreibers.
- Drei zusammenhängende Paper zu A, B und Kopplung/Reichweite.
- Konkrete Benchmarkwahl, Messgrößen, Stichprobe und statistischer Schätzer.
- Eventuelle zweite Anwendungsdomäne und technische Erweiterungen.

### Explizit offen

- Vollständige Neuheitsabsicherung und Reproduzierbarkeit der engsten Konkurrenz.
- Persönliche Clusterzuteilung, reale Laufzeiten und finanzielles Budget.
- Betreuung, gültige Promotionsordnung, kumulative Anforderungen und Publikationsstatus.
- Inhaltliche und rechtliche Eignung der späteren Umgebungen und Datenverteilung.
- Ob ein eigener Algorithmus nötig ist oder ein präziser empirischer Befund den ersten Beitrag bildet.

Drei Papers sind ein Planungsziel, keine verifizierte Pflicht und keine Zusage. Bei neuen Befunden wird der spezifische Untersuchungsfall revidiert, nicht unbemerkt das gesamte Vorhaben gewechselt.

## 8. Nichtziele und konservierte Alternativen

Im ersten Abschnitt keine offene motorische Skill-Discovery, kein großes RL- oder VLA-Training, kein neues Foundation Model, keine neue Spielengine und kein obligatorischer Benchmarkbau. Kein AGI-Beweis, keine „wahre Persönlichkeit“ eines Modells, kein subjektives Angst-/Trauma-Maß.

XAI ist zunächst unterstützende Diagnostik. Kausalitätsforschung, Failure Attribution, Model Routing, Body-Effizienz, Skill-Komposition und Skill-Transfer bleiben dokumentierte Optionen. Keine davon darf ohne neue Nutzerentscheidung A oder B verdrängen.

Insbesondere gilt nicht die frühere Behauptung, ein positiver faktorieller Interaktionsterm beweise eine besondere Mind–Body-Symbiose. Schnittstellen-Inkompatibilität und triviale serielle Erfolgsabhängigkeiten müssen berücksichtigt werden. Historische Prozentanteile des „Gehirns“ werden nicht aus Snapshot-Kreuzungen behauptet.

## 9. Technische Architektur: unveränderte Grenzen

Normative Zielhierarchie gemäß `02_ARCHITECTURE_CANONICAL.md`:

`GameInstance → Capture / optionale Visible-State Bridge → No-Spoiler Firewall → Perception/Observation → Temporal State → Memory Retrieval → LLM Cortex → Manager/Executive → Grounded Skill Contract → Body + bounded Reflex → SafetyFilter/InputExecutor → GameInstance → Visible Outcome → Independent Verifier → Memory + Replay`

Zwischen Runs kann ein SkillTrainer später neue Body-Versionen erzeugen. Für den ersten Forschungsabschnitt bleiben Modell- und Body-Gewichte sowie der deklarierte Harness innerhalb der jeweiligen Studie fix; zulässiger Erfahrungs-/Wissenszustand darf nach dem Studienprotokoll wachsen.

### Klare Zuständigkeiten

- Cortex: abstrakte Ziele, Hypothesen, offene Fragen, Vorschläge und erwartete sichtbare Folgen. Keine primitive Tastenkontrolle, auch nicht unter dem Namen „Micro-Intent“.
- Manager: Capability-Prüfung, Grounding, Scheduling, Budgets, Vertragsgrenzen und Auswahl der Verifikation. Keine ungegroundeten Ziele an den Body weiterreichen.
- Body: schnelle universelle Ausführung innerhalb eines aktiven Contracts. Ein fixer heuristischer Body ist ein zulässiger Bootstrap. Keine spielbezogenen Lösungsroutinen.
- Reflex: nur im aktiven Contract; keine neuen Ziele, erweiterten Budgets oder Safety-Ausnahmen.
- Verifier: unabhängige sichtbare Outcomes. Ein Screenshotwechsel, Textstil oder LLM-Erfolgskommentar ist kein Beweis.
- InputExecutor: Fokusprüfung, Rate Limits, Emergency Stop und Logging; echte Eingaben und Spielstart nur nach ausdrücklicher Autorisierung.

Ein schwacher, aber ausführbarer Skill und eine nicht vorhandene/ungegroundete Fähigkeit sind verschiedene Dinge. Keine neue Statusmaschine oder API wird allein durch diesen Satz als implementiert vorausgesetzt.

## 10. No-Spoiler, Daten und Run-Modi

Die Regeln aus `04_RESEARCH_PROTOCOL_CANONICAL.md` bleiben unverändert. Offizielle Runs nutzen ausschließlich zugelassene sichtbare Information und eigene zulässige Vorgeschichte. Keine Guides, Wikis, Walkthroughs, dataminten Maps, internen RPG-Maker-IDs, Switches/Variables, Savegame-Interna oder RAM-/Process-State als Agentenwissen.

- `screen-only`: primäre offizielle lokale/offline Kohorte.
- `bridge-assisted`: gesonderte offizielle Diagnosekohorte, nur allowlisted gleichzeitig sichtbare Werte mit Screenshotbindung.
- `debug`: nicht headline-eligible; kein allgemeiner Freibrief für Hidden-State-Zugriff.
- `networked-api-exploratory`: separate API-/Capability-Ceiling-Exploration. Nicht mit offiziellen Offline-Ergebnissen poolen.
- `contaminated`: permanente Quarantäne bei entsprechendem Integritätsbruch; nicht zu zulässigem Memory oder Training zurückbefördern.

Ein künftiges wissenschaftliches API-Protokoll oder ein Benchmark mit evaluator-only Hidden State benötigt ein explizites eigenes freigegebenes Protokoll. Es ist **nicht** durch dieses Organisationsdokument freigegeben. Evaluatorlabels, Spoiler und Forschungsnotizen dürfen nicht in offizielle Agentenprompts, Memory oder Training gelangen. Auch der Ursprungschat enthält Spielwissen und ist **keine Agentendatenquelle**.

„Ohne Vorwissen“ heißt keine zusätzlich bereitgestellte zielspielspezifische Lösung/Demonstration oder trainierte Spezialpolicy. Latente Vortrainingsexposition wird nicht ausgeschlossen. „Learning by Doing“ heißt zu Beginn externe Memory-Anpassung, nicht automatisch Gewichtslernen.

## 11. Minimaler Forschungsapparat und Pilotfolge

Vor neuer Implementierung erfolgt der von Anton verlangte **T0-Alignment-Review**. Er prüft HEAD, aktuelle Issues, existierende Contracts, bestmögliche einfache Ansätze und die Messanforderungen aus A/B. Er soll wenige Entscheidungen ermöglichen, nicht unbegrenzt alle Architekturen vergleichen.

Danach wird der kleinste bereits passende Roadmap-Schritt wieder aufgenommen. Laufende Milestones ändern sich nicht automatisch durch neue Paperideen. Spätere Instrumentierung wird in separate kleine Issues zerlegt.

Geplanter Pilot: ein neutraler lokaler Cortex, ein fixer generischer Body, endliche Budgets, sichtbare eigene Erfahrung, unabhängig bestimmtes Outcome und auditierbare Datenspur. Erst nach dem Closed Loop folgen gezielte Persona-Konfigurationen, Retrieval-Snapshots und Synthese-Provenienz.

Bestehende No-action- und Fixed-goal-Kontrollen des kanonischen Piloten bleiben im T0-/Studienabgleich zu berücksichtigen. Sie sind nicht automatisch die einzige oder hinreichende wissenschaftliche Baseline für A/B. Ihre operative Zuordnung wird explizit dokumentiert, nicht durch neue Forschungsbezeichnungen still entfernt.

Ein möglicher Forschungs-Mindestdatensatz enthält Experiment-/Linien-/Run-/Welt-IDs, Modell/Prompt/Persona/Config/Body/Verifier-Identität, Inputkontext, tatsächlich ausgeliefertes Retrieval, Zielvorschlag, Manager-Reaktion, Ausführung, sichtbares Outcome und Kosten. **Das sind Forschungsanforderungen; kein vollständiges Schema ist hier als implementiert behauptet.** Welche Felder unmittelbar nötig sind, entscheiden T0 und das Studienprotokoll gemeinsam.

Modell- oder Body-Training nur zwischen Runs, nach stabiler Outcome-Messung, mit Holdout-Validation, Versionierung und Rollback. Keine willkürlichen LLM-Scalar-Rewards. Im ersten Abschnitt kein separat verpflichtendes Body-Vortraining als Forschungsziel.

## 12. Messprinzipien ohne überzogene Claims

- Pro bestätigender Studie ein vorab spezifizierter primärer Kontrast und Endpunkt. Kein beliebiger „Fortschrittsscore“ aus Räumen, Bossen und Itemzahlen.
- Für A kann ein unabhängig operationalisiertes Verhalten bei vergleichbaren Gelegenheiten primär sein. Für B/C ist späterer externer Zielerfolg unter deklariertem Budget naheliegend. Exakte Endpunkte sind offen.
- Meilensteine sind gegebenenfalls Evaluationslabels, keine heimlichen Lösungshinweise. Jede Definition muss beobachtbar beziehungsweise durch ein gesondertes zulässiges Benchmarkprotokoll legitimiert sein.
- Bei vererbtem Memory sind Agentenlinien die unabhängigen Einheiten; Runs und Aktionen sind verschachtelt. Die ältere run-basierte Pilotregel wird nicht unbesehen auf Longitudinalstudien übertragen.
- Gleicher Seed ist nach verschiedenen Aktionen kein identischer Verlauf. Stochastik erfordert Wiederholungen, geeignete Randomisierung/Blockung und Unsicherheitsintervalle.
- Refusals, ungültige Outputs, Timeouts, Ablehnungen, Tod und Stillstand bleiben sichtbar. Integritätsbruch und gewöhnliches Scheitern bleiben getrennt. Tod ist nicht pauschal harmlose Zensierung.
- Rohmaterial und nicht identifizierbare Fälle bewahren. Raterübereinstimmung ersetzt keine inhaltliche Validität.
- Deklarierte Gründe sind Outputs, kein Lesen privater Gedanken. Memory-Löschung zeigt bestenfalls eine unter der Intervention gemessene Inputabhängigkeit; redundante Belege und Verteilungsverschiebungen begrenzen die Interpretation.
- Erwerb, Konsolidierung, Inferenz, Evaluation und Training kosten Ressourcen. Keine Zusatzaufrufe als kostenloser Vorteil, kein beliebiger gemeinsamer Einheitskostenwert.
- Positive und negative Ergebnisse brauchen genügend Präzision. Ein fehlgeschlagener Prototyp ist noch kein belastbarer Negativbefund über LLMs.

Das spätere Mess-/Studienprotokoll präzisiert diese Regeln; dieses Dokument ersetzt es nicht.

## 13. Literatur, Beiträge und Betreuung

Frühere Chatantworten, Gap-Matrizen und Forschungspläne sind Recherchevorarbeit. Ihre Titel, Autoren, Jahrgänge, Zahlen und behaupteten Limits müssen vor wissenschaftlicher Verwendung an Primärquellen geprüft werden. „In diesem Handoff genannt“ bedeutet nicht „verifiziert“. Literaturbefund, Autoren-Future-Work, eigene Ableitung und Projektentscheidung bleiben getrennt.

Möglicher Beitragsbogen: A (Instruktion und Erfahrungsgewinn), B (episodenübergreifende Synthese), C (Persistenz/Reichweite/Kopplung). Titel sind Arbeitsnamen. Eine technische Infrastruktur ist nur dann ein eigener wissenschaftlicher Beitrag, wenn der Erkenntnisgewinn und Vergleich dies tragen.

Zuerst soll ein Betreuer das Vorhaben nachvollziehen können. Genannte Wunschkontakte: Prof. Dr. Christoph Weisser und Prof. Dr. Frederik Bäumer. Ihre aktuelle Rolle, Betreuungskapazität, institutionelle Zuständigkeit und Promotionsordnung sind vor Kontakt/Behauptungen zu prüfen; es gibt keine bestätigte Zusage. Keine eigenmächtige Kontaktaufnahme.

Vorhandene Ressourcen laut Nutzer: Ryzen „9800xd“ (genaue Bezeichnung lokal bestätigen), RX 6900 XT, 32 GB DDR5, 2 TB SSD. HSBI-Cluster ist eine Möglichkeit, keine zugesicherte Zuteilung. Der erste technische Pilot soll nicht von großem Clustertraining abhängen.

## 14. Verhältnis zu älteren Quellen und Festschreibung

Die Baseline `00–06` vom 1. September 2026 bleibt inhaltlich erhalten. Dieses Addendum präzisiert die **aktuelle Schwerpunktsetzung** und ordnet die erste Arbeitsteilung. Es ersetzt weder Sicherheitsregeln noch Source-Level-Belege.

Frühere Forschungsoptionen und Working-Paper-RQs behalten ihren historischen Status. Die Hauptfragen dieses Programms heißen vorläufig **A/B/C**, nicht umnummerierte RQ1–RQ3 des alten Manuskripts. Die vollständigen Mapping- und Konfliktregeln stehen im aktiven Quellenindex.

Künftige Änderungen an Fokus, Run-Modi, Primärendpunkten oder architektonischen Zuständigkeiten brauchen einen Änderungsantrag, die zuständige fachliche Prüfung und Antons Entscheidung. Kleine lokale Implementierungen und Textredaktion brauchen keine Grundsatzfreigabe, solange der erteilte Auftrag und die Referenzversion eingehalten werden.

## 15. Nachweisgrundlage dieses Dokuments

- Nutzerentscheidungen im Ursprungschat: Auswahl A/B, Erfahrung als Kern, Fixed-Body-Pilot, Skill-Komposition/Transfer optional, wissenschaftliche Vorsicht und zuletzt explizite Trennung in zwei Orchestratoren mit vorgeschaltetem Technikreview.
- `01_PROJECT_CHARTER.md`, `02_ARCHITECTURE_CANONICAL.md`, `03_RESEARCH_ROADMAP_CANONICAL.md`, `04_RESEARCH_PROTOCOL_CANONICAL.md`, Baseline 2026-09-01.
- Forschungsplan `Forschungsplan_v1_0.md`, Arbeitsfassung 2026-09-06, im vorherigen Arbeitspaket; neue Ausrichtung, ausdrücklich kein empirischer Nachweis.
- Das Working Paper v2 ist historische präempirische Vorarbeit. Sein Implementierungssnapshot bleibt zeitgebunden.

Die aktuelle Repository-Prüfung steht absichtlich **nicht** hier als Live-Zustand, sondern im gesonderten Bootstrap-Snapshot. Die Referenzquellen dieses Dokuments und ihre Dateihashes sind im Paketmanifest verzeichnet.
