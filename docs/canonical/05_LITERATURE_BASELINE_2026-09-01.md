# Frozen Literature Baseline — Autonomous Game and Embodied Agents

**Snapshot date:** 2026-09-01  
**Status:** canonical literature baseline for project context. This file is intentionally frozen across ordinary milestones. It summarizes the research basis used to choose the project architecture; later research may supplement it without silently changing this baseline.

---

**Stand:** 1. September 2026  
**Zweck:** Quellenbasis und Design-Transfer für den Fear-&-Hunger-Cortex–Body-Agenten  
**Lesart:** Die Liste unterscheidet zwischen belastbaren peer-reviewten Arbeiten, öffentlichen Forschungsberichten und neueren Preprints. Keine einzelne Arbeit beweist, dass die vorgeschlagene Pipeline ein unbekanntes RPG vollständig bewältigen kann.

## Evidenzstufen

- **A — peer-reviewed/etabliert:** Konferenz-/Journalpublikation oder grundlegende Theorie.
- **B — belastbarer öffentlicher Forschungsbericht/Preprint:** Primärquelle mit ausreichenden Methodenangaben, aber nicht notwendigerweise abschließend begutachtet.
- **C — neuer Benchmark/Preprint:** hochrelevant, aber Resultate und Schlussfolgerungen sind vorläufiger zu behandeln.

---

## 1. Direkt relevante hierarchische Game-/Embodied-Agenten

### [R01] SIMA 2: A Generalist Embodied Agent for Virtual Worlds — 2025 — Evidenz B

**Quelle:** SIMA Team et al.  
**Primärquelle:** https://arxiv.org/abs/2512.04797

**Architektur/Methodik**

- Gemini-basiertes multimodales Embodied Model.
- Input über sichtbare virtuelle Welten; Output über menschliche Interaktionsschnittstelle.
- High-Level-Reasoning kann hierarchisch mit einem stärkeren Modell kombiniert werden.
- Self-Improvement mit automatisch erzeugten Tasks und einem separaten Reward-Modell.
- Erfahrungen werden zur Verbesserung späterer Agentengenerationen verwendet.

**Transfer auf unser Projekt**

- unterstützt langsamer Cortex + schneller Controller;
- unterstützt separaten Task Setter/Curriculum und Reward Judge;
- unterstützt generationsweises statt unkontrolliertem In-Run-Training;
- bestätigt, dass lange Horizonte, Memory und präzise Low-Level-Control weiterhin Engpässe sind.

**Nicht übernehmen**

- Training eines großen VLA/Foundation-Modells;
- großer proprietärer Demonstrations-/Compute-Stack;
- einheitliches Modell als alleinige Wahrnehmungs-, Reasoning- und Motorikinstanz.

---

### [R02] SIMA: Scalable Instructable Multiworld Agent — 2024 — Evidenz B

**Quelle:** SIMA Team et al.  
**Primärquelle:** https://arxiv.org/abs/2404.10179  
**Offizielle Projektseite:** https://deepmind.google/discover/blog/sima-generalist-ai-agent-for-3d-virtual-environments/

**Architektur/Methodik**

- Screenshots/Bilddaten plus Sprachinstruktion;
- Keyboard-/Mouse-ähnliche Actions;
- Training über mehrere virtuelle Welten;
- instruction-conditioned, generalistische Ausführung.

**Transfer**

- ein gemeinsames conditioned Body-Modell ist plausibler als ein Modell pro Skill;
- standardisierte menschliche Schnittstelle fördert spätere Generalisierung;
- Skill-Level-Instruktionen sind geeigneter als primitive Key-Sequenzen.

**Grenze**

- überwiegend kürzere Skills; keine Lösung für unser langfristiges Memory-/Theory-Building.

---

### [R03] Game On: Towards Language Models as RL Experimenters — 2024 — Evidenz B

**Quelle:** Jingwei Zhang, Thomas Lampe, Abbas Abdolmaleki, Jost Tobias Springenberg, Martin Riedmiller  
**Primärquelle:** https://arxiv.org/abs/2409.03402

**Architektur**

Drei Hauptmodule:

1. **Curriculum Module**
   - Task Proposition;
   - Task Decomposition;
   - Skill Retrieval;
   - Historie erfolgreicher/gescheiterter Episoden.

2. **Embodiment Module**
   - Skill Library;
   - language-conditioned Actor-Critic;
   - Rollouts und Datensammlung;
   - Offline Policy Iteration.

3. **Analysis Module**
   - Lernkurven überwachen;
   - Konvergenz beurteilen;
   - Skills zur Library hinzufügen.

Die konkrete Arbeit verwendet Gemini 1.5 Pro als High-Level-System und einen text-conditioned Perceiver-Actor-Critic. Der Proof of Concept startet mit vorhandenem Skillset und ungefähr einer Million Episoden; die Policy hat etwa 140M Parameter.

**Transfer**

- stärkste direkte Vorlage für Cortex als Curriculum-/Skill-Experimenter;
- Skill Retrieval darf fehlschlagen und eine Capability Gap signalisieren;
- der Low-Level-Body wird offline aus gesammelten Erfahrungen verbessert;
- Skill Certification gehört in ein getrenntes Analysis-Modul.

**Nicht übernehmen**

- Größe des PAC-/Datensystems;
- freie sprachliche Skill-Bezeichnungen ohne typisierte Contract-Grenze;
- fixe Skill-Dauern in dynamischen Spielen;
- fehlende automatisierte Reward-/Verifier-Lösung.

---

### [R04] JARVIS-1: Open-World Multi-Task Agents with Memory-Augmented Multimodal Language Models — 2023/2025 — Evidenz A/B

**Quelle:** Zihao Wang et al.  
**Primärquelle:** https://arxiv.org/abs/2311.05997  
**Journal:** IEEE TPAMI, DOI 10.1109/TPAMI.2024.3511593  
**Code:** https://github.com/CraftJarvis/JARVIS-1

**Architektur**

- multimodaler Language-Model-Planner;
- visuelle Observation + Textinstruction → Plan;
- Plan wird an goal-conditioned Controller delegiert;
- multimodales Memory kombiniert Vorwissen und tatsächliche Spielerfahrung.

**Transfer**

- unmittelbare Evidenz für Planner → goal-conditioned Controller;
- persistentes Erfahrungs-Memory für Long-Horizon;
- klare Trennung zwischen Planen und verkörperter Ausführung.

**Grenze**

- nutzt Minecraft-spezifisches Vorwissen/Pretraining;
- Teile der multimodalen Memory-/Learning-Komponenten waren im öffentlichen Repository nicht vollständig verfügbar;
- deshalb keine direkte Implementierungsvorlage für No-Spoiler-Runs.

---

### [R05] Voyager: An Open-Ended Embodied Agent with Large Language Models — 2023 — Evidenz B

**Quelle:** Guanzhi Wang et al.  
**Primärquelle:** https://arxiv.org/abs/2305.16291  
**Projekt:** https://voyager.minedojo.org/

**Architektur**

- automatisches Curriculum;
- stetig wachsende Skill Library aus ausführbarem JavaScript;
- semantisches Skill Retrieval;
- iterative Verbesserung aus Environment Feedback, Execution Errors und Self-Verification;
- GPT-4 Blackbox, keine Gewichtsupdates.

**Transfer**

- Skill Library als prozedurales Gedächtnis;
- Curriculum orientiert sich an Exploration und aktueller Kompetenz;
- Skills müssen versioniert, wiederverwendbar und kompositional sein;
- Feedback-/Failure-Loop ist wichtiger als Single-Shot-Planung.

**Nicht übernehmen**

- LLM-generierter ausführbarer Controller-Code;
- Mineflayer/API als privilegierte Action-/State-Schnittstelle;
- Self-Verification ohne unabhängigen Verifier;
- spielbezogene Skill-Funktionen.

---

### [R06] Cradle: Empowering Foundation Agents towards General Computer Control — ICML 2025 — Evidenz A

**Quelle:** Weihao Tan et al.  
**Primärquelle:** https://proceedings.mlr.press/v267/tan25h.html  
**ICML-Seite:** https://icml.cc/virtual/2025/poster/46393

**Architektur**

- general computer control;
- Screenshot-Input, Keyboard-/Mouse-Output;
- Module: Information Gathering, Self-Reflection, Task Inference, Skill Curation, Action Planning, Memory;
- LMM erzeugt nach High-Level-Planung ausführbaren Low-Level-Code.

**Transfer**

- echte Commercial Games und standardisierte menschliche Schnittstelle sind machbar;
- modulare Harness-Komponenten sind für Long-Horizon notwendig;
- Memory, Task Inference und Skill Curation sollten getrennte Verantwortungen bleiben.

**Nicht übernehmen**

- direkte Codeausführung als Motorik;
- fehlende harte Manager-/Input-Grenze;
- schwer attribuierbare Vermischung von LMM-Reasoning und Low-Level-Control.

---

### [R07] GLIDER: Divide and Conquer — ICML 2025 — Evidenz A

**Quelle:** Zican Hu et al.  
**Primärquelle:** https://arxiv.org/abs/2505.19761  
**PMLR:** https://proceedings.mlr.press/v267/hu25q.html

**Architektur**

- High-Level-LLM-Policy;
- Offline Hierarchical RL;
- abstrakte Schrittpläne beaufsichtigen einen Low-Level-Controller;
- task-agnostic Low-Level-Skills;
- schnelle Adaptation an nichtstationäre Umgebungen.

**Transfer**

- theoretisch/empirisch starke Unterstützung für Cortex–Body;
- abstrakte, task-agnostische Skills sind das richtige Delegationsniveau;
- Offline-Daten können die Low-Level-Ausführung verbessern.

**Grenze**

- ScienceWorld/ALFWorld unterscheiden sich deutlich von real-time pixel-level RPG-Steuerung.

---

### [R08] SayCan: Do As I Can, Not As I Say — CoRL 2022 — Evidenz A

**Quelle:** Michael Ahn et al.  
**Primärquelle:** https://arxiv.org/abs/2204.01691  
**Projekt:** https://say-can.github.io/

**Architektur**

- LLM schlägt Skill-Sequenzen vor;
- Skill-Affordance/Value Functions bewerten Ausführbarkeit in aktuellem Zustand;
- Auswahl kombiniert sprachliche Nützlichkeit und verkörperte Machbarkeit.

**Transfer**

- Cortex darf nur aus tatsächlich verfügbaren Skills wählen;
- Skill Competence muss in die Auswahl einfließen;
- Manager fungiert als Capability-/Affordance-Gate;
- ein plausibler LLM-Plan ist ohne ausführbaren Skill wertlos.

---

## 2. Low-Level-Policies, Behavior Priors und Skill Conditioning

### [R09] Video PreTraining (VPT) — 2022 — Evidenz B

**Quelle:** Bowen Baker et al. / OpenAI  
**Primärquelle:** https://arxiv.org/abs/2206.11795  
**Offizielle Seite:** https://openai.com/index/vpt/

**Methodik**

- Inverse Dynamics Model labelt große Mengen unlabeled Gameplay;
- Behavior Cloning aus etwa 70.000 Stunden Video;
- native Keyboard-/Mouse-Schnittstelle;
- RL-Finetuning für schwierige Langzeittasks.

**Transfer**

- Behavior Prior/BC ist ein sinnvoller Bootstrap vor RL;
- native menschliche Action-Schnittstelle ist generalisierbar;
- kleine eigene Demonstrationsmengen können Skill-Lernen stabilisieren.

**Nicht übertragbar**

- Daten- und Compute-Skala;
- spielbezogene Internetvideos widersprechen unserem No-Spoiler-Ziel.

---

### [R10] STEVE-1 — NeurIPS 2023 — Evidenz A

**Quelle:** Shalev Lifshitz et al.  
**Primärquelle:** https://proceedings.neurips.cc/paper_files/paper/2023/hash/dd03f856fc7f2efeec8b1c796284561d-Abstract-Conference.html

**Methodik**

- instruction-tuned VPT;
- MineCLIP-Latent als Goal Conditioning;
- self-supervised Behavior Cloning;
- Hindsight Relabeling;
- Raw Pixels und Low-Level Keyboard/Mouse.

**Transfer**

- shared goal-conditioned Body;
- Hindsight-Relabeling für tatsächlich erreichte sichtbare Ziele;
- Language/Goal Conditioning über getrennte Goal-Repräsentation;
- Pretraining/BC vor RL.

**Grenze**

- basiert auf großen bereits trainierten Minecraft-Modellen.

---

### [R11] DreamerV3 — Nature 2025 — Evidenz A

**Quelle:** Danijar Hafner, Jurgis Pašukonis, Jimmy Ba, Timothy Lillicrap  
**Primärquelle:** https://doi.org/10.1038/s41586-025-08744-2

**Methodik**

- learned world model;
- Actor/Critic lernen in imaginierten Zukunftstrajektorien;
- eine Konfiguration über mehr als 150 Tasks;
- Minecraft-Diamond aus Pixeln und sparse rewards;
- einzelne Experimente auf Nvidia A100.

**Transfer**

- späterer Kandidat, wenn reale Interaktionen knapp und genügend Replaydaten verfügbar sind;
- World Model kann Body-Sample-Efficiency verbessern;
- starker Vergleichspunkt für spätere Dissertation.

**Nicht als Start**

- zu hohe Architektur-, Debugging- und Compute-Komplexität;
- löst nicht automatisch No-Spoiler, Memory und semantische Planung.

---

### [R12] PPO — 2017 — Evidenz A

**Quelle:** John Schulman et al.  
**Primärquelle:** https://arxiv.org/abs/1707.06347

**Transfer**

- robuste, einfache On-Policy-Baseline;
- geeignet für diskrete Body-Actions;
- RecurrentPPO/MaskablePPO über SB3-Contrib verfügbar;
- zuerst Frame Stacking als einfachere Baseline testen.

---

### [R13] Hindsight Experience Replay — NeurIPS 2017 — Evidenz A

**Quelle:** Marcin Andrychowicz et al.  
**Primärquelle:** https://arxiv.org/abs/1707.01495

**Transfer**

- fehlgeschlagene `reach_target`-Trajektorie kann mit einem tatsächlich erreichten sichtbaren Ziel relabelt werden;
- nur für klar messbare Goal-Spaces;
- nicht für semantische langfristige RPG-Strategien verwenden.

---

## 3. Hierarchical RL und formale Skills

### [R14] Between MDPs and Semi-MDPs: Options — 1999 — Evidenz A

**Quelle:** Richard S. Sutton, Doina Precup, Satinder Singh  
**DOI:** https://doi.org/10.1016/S0004-3702(99)00052-1

**Transfer**

Ein Skill wird als temporär erweiterte, geschlossene Policy verstanden:

- Initiation/Preconditions;
- interne Policy;
- Termination.

Dies ist die formale Grundlage für unsere Skill Contracts.

---

### [R15] The Option-Critic Architecture — AAAI 2017 — Evidenz A

**Quelle:** Pierre-Luc Bacon, Jean Harb, Doina Precup  
**DOI:** https://doi.org/10.1609/aaai.v31i1.10916

**Transfer**

- interne Skill-Policy und Termination können prinzipiell gemeinsam gelernt werden;
- für uns erst später relevant;
- zunächst bleiben Preconditions/Termination explizit und verifiziert, um Reward-Hacking zu vermeiden.

---

## 4. Memory, Reasoning und Reflexion

### [R16] ReAct — ICLR 2023 — Evidenz A

**Quelle:** Shunyu Yao et al.  
**Primärquelle:** https://arxiv.org/abs/2210.03629

**Transfer**

- Reasoning und Environment Action sollten iterativ gekoppelt sein;
- in unserem System jedoch auf Contract-/Event-Ebene, nicht primitive Actions;
- strukturierter Decision Trace statt ungeprüfter freier Gedankenprotokolle.

---

### [R17] Reflexion — NeurIPS 2023 — Evidenz A

**Quelle:** Noah Shinn et al.  
**Primärquelle:** https://papers.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html

**Transfer**

- Trial-and-Error kann ohne LLM-Gewichtsupdate über episodisches Reflexionsmemory verbessert werden;
- Death-Post-Mortems und Folgeexperimente passen dazu;
- Reflexion bleibt Hypothese und wird nicht automatisch zum Fakt.

---

### [R18] Optimus-1: Hybrid Multimodal Memory — 2024 — Evidenz B

**Quelle:** Zaijing Li et al.  
**Primärquelle:** https://arxiv.org/abs/2408.03615

**Architektur**

- Hierarchical Directed Knowledge Graph;
- Abstracted Multimodal Experience Pool;
- Knowledge-guided Planner;
- Experience-driven Reflector.

**Transfer**

- explizites semantisch/topologisches Wissen plus Episodenpool ist geeigneter als nur Vector RAG;
- Planner und Reflector können getrennt evaluiert werden;
- unser Evidence Ledger muss jede Abstraktion auf Rohbeobachtungen zurückführen.

---

## 5. Verifier, Rewards und automatische Curricula

### [R19] Eureka — ICLR 2024 — Evidenz A

**Quelle:** Yecheng Jason Ma et al.  
**Primärquelle:** https://arxiv.org/abs/2310.12931  
**Projekt:** https://eureka-research.github.io/

**Methodik**

- LLM generiert Reward-Code;
- Kandidaten werden durch RL-Training/evolutionäre Evaluation getestet;
- Reward Reflection verbessert spätere Kandidaten.

**Transfer**

- Cortex darf Reward-/Verifier-Kandidaten vorschlagen;
- Kandidaten brauchen automatische Evaluation und Freigabe;
- Reward Design kann selbst Forschungsgegenstand sein.

**Nicht übernehmen**

- unvalidierter LLM-Code im Live-Agenten;
- Hidden-Simulator-State als selbstverständliche Reward-Quelle.

---

### [R20] Vision-Language Models as a Source of Rewards — 2023 — Evidenz B

**Quelle:** Kate Baumli et al.  
**Primärquelle:** https://arxiv.org/abs/2312.09187

**Transfer**

- visuelle Goal-Rewards aus VLMs sind möglich;
- spätere Option für semantische Outcomes;
- größere Modelle erzeugen tendenziell bessere Reward-Signale.

**Grenze**

- VLM-Reward kann räumlich/semantisch falsch sein und braucht Calibration, Abstention, negative Beispiele und Human Audit.

---

### [R21] MineDojo / MineCLIP — NeurIPS 2022 — Evidenz A

**Quelle:** Linxi Fan et al.  
**Primärquelle:** https://proceedings.neurips.cc/paper_files/paper/2022/hash/74a67268c5cc5910f64938cac4526a90-Abstract.html  
**Projekt:** https://minedojo.org/

**Transfer**

- Video-Language-Modelle können freie Sprachziele als Reward/Ähnlichkeit operationalisieren;
- standardisierte Tasks, Daten und Agentenarchitektur sind zentral.

**Nicht übernehmen**

- Internet-Wissensbasis, Tutorials und Wiki-Daten sind mit unserem No-Spoiler-Protokoll unvereinbar.

---

## 6. Benchmarks und negative Befunde

### [R22] BALROG — ICLR 2025 — Evidenz A

**Quelle:** Davide Paglieri et al.  
**Primärquelle:** https://proceedings.iclr.cc/paper_files/paper/2025/hash/f0b1515be276f6ba82b4f2b25e50bef0-Abstract-Conference.html

**Befund**

- aktuelle LLMs/VLMs brechen bei komplexen dynamischen Games stark ein;
- visuelle Repräsentation kann Performance sogar verschlechtern;
- Spatial Reasoning, Exploration und Long-Horizon bleiben offen.

**Konsequenz**

- Perception darf nicht als gelöst angenommen werden;
- Text-/Bridge- und Screen-Bedingungen getrennt evaluieren;
- einfache Heuristiken und negative Controls sind Pflicht.

---

### [R23] The PokeAgent Challenge — 2026 — Evidenz C

**Quelle:** Seth Karten et al.  
**Primärquelle:** https://arxiv.org/abs/2603.15563

**Befund/Architektur**

- standardisiertes RPG-Speedrunning;
- modularer, reproduzierbarer LLM-Harness;
- deutliche Lücke zwischen Generalist LLM, Spezialist RL und Elite-Mensch;
- RPGs messen Fähigkeiten, die klassische LLM-Benchmarks nicht erfassen.

**Konsequenz**

- Harness×Model-Matrix;
- Milestones statt nur Completion;
- Long-Context, Memory, Navigation und Verifier explizit messen;
- Gaming ist ein legitimer Long-Horizon-Forschungsgegenstand.

---

### [R24] GameWorld — 2026 — Evidenz C

**Quelle:** Mingyu Ouyang et al.  
**Primärquelle:** https://arxiv.org/abs/2604.07429

**Befund**

- 34 Games, 170 Tasks;
- Computer-Use-Actions versus semantische Actions;
- state-verifiable Outcome Metrics;
- beste Agenten bleiben weit unter Menschen;
- Latenz, sparse feedback und irreversible Fehler sind zentrale Probleme.

**Konsequenz**

- unsere Hierarchie sollte semantic Skill Tasks und native Inputs vergleichbar machen;
- Verifier und Action Validity sind primäre Komponenten;
- Completion allein reicht nicht.

---

### [R25] PokeGym — 2026 — Evidenz C

**Quelle:** Ruizhi Zhang et al.  
**Primärquelle:** technischer Bericht, April 2026

**Befund**

- raw RGB und langhorizontige RPG-Aufgaben;
- physischer Deadlock/Recovery ist oft wichtiger als abstraktes Reasoning;
- schwächere Modelle erkennen Deadlocks nicht; stärkere erkennen sie, können sie aber nicht auflösen.

**Konsequenz**

- Temporal State, No-Progress und `recover_from_no_progress` sind frühe Kernfähigkeiten;
- nicht jedes Scheitern ist ein Cortex-Fehler.

---

### [R26] Continual Harness — 2026 — Evidenz C

**Quelle:** Seth Karten et al.  
**Primärquelle:** https://arxiv.org/abs/2605.09998

**Ansatz**

- Harness selbst wird fortlaufend angepasst;
- Prompt, Subagents, Skills und Memory können aus Trajektorien weiterentwickelt werden;
- Prozess-Reward-Co-Learning.

**Transfer**

- Harness-Versionierung und lernende Agenteninfrastruktur sind zukünftige Forschungsfelder;
- Erfahrungen sollten nicht nur Modellgewichte, sondern auch Retrieval-/Prompt-/Skill-Contracts verbessern können.

**Vorsicht**

- sehr neue Arbeit;
- für den ersten Pilot bleiben Harness und Policy innerhalb einer Runserie eingefroren.

---

## 7. Implementierungs-/Modellquellen

### [R27] Stable-Baselines3 PPO/Contrib

- PPO-Dokumentation: https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html
- RecurrentPPO/MaskablePPO: https://sb3-contrib.readthedocs.io/
- Custom Environments: https://stable-baselines3.readthedocs.io/en/master/guide/custom_env.html

**Projektentscheidung**

- Frame Stacking zuerst;
- RecurrentPPO nur nach Baseline;
- `check_env`;
- Action Mask für Contract-Grenzen;
- BC bleibt separate Baseline.

---

### [R28] PaddleOCR

- Repository: https://github.com/PaddlePaddle/PaddleOCR
- Dokumentation: https://www.paddleocr.ai/

**Projektentscheidung**

- lokale, gepinnte OCR-Pipeline;
- eigene F&H-ROI-/Holdout-Messung;
- keine allgemeine Dokument-Benchmark auf Spieltext übertragen;
- OCR-Confidence und Evidence pro Span.

---

### [R29] OpenAI gpt-oss

- Offizielle Quelle: https://openai.com/index/introducing-gpt-oss/

**Projektentscheidung**

- `gpt-oss-20b` als lokaler text-only Cortex-Kandidat;
- ungefähr 16 GB Speicherklasse;
- `gpt-oss-120b` nur mit 80-GB-/HPC-Ressourcen;
- provider-agnostische OpenAI-kompatible Schnittstelle.

---

### [R30] OpenAI API-Modelle und Preise, Stand 1. September 2026

- Modellübersicht: https://platform.openai.com/docs/models
- Luna: https://developers.openai.com/api/docs/models/gpt-5.6-luna
- Terra: https://developers.openai.com/api/docs/models/gpt-5.6-terra
- Preisübersicht: https://help.openai.com/en/articles/20001415

**Projektentscheidung**

- Modellnamen und Preise niemals im Domain-Code festschreiben;
- manuelle Config-Auswahl;
- lokale Baseline + API-Ablation;
- Event-getriebene Calls und Token-/Kostenlogging.

---

## 8. Literaturgeleitete Projektentscheidungen

1. **Cortex–Body-Hierarchie bleibt.**  
   Gestützt durch JARVIS-1, GLIDER, SayCan, Game On und SIMA 2.

2. **Body wird shared und goal-conditioned.**  
   Gestützt durch SIMA, Game On, JARVIS-1, VPT/STEVE-1.

3. **Skill Library speichert Contracts und Policies, nicht nur Code.**  
   Inspiriert von Voyager und Options; angepasst an sichere Low-Level-Control.

4. **Skill-Lernen ist ein eigener Experimentloop.**  
   Gestützt durch Game On und SIMA 2.

5. **Verifier ist getrennt vom Cortex.**  
   Gestützt durch SIMA 2, Game On, GameWorld und Reward-Literatur.

6. **Death führt zu evidenzgebundener Reflexion, nicht sofort zu Facts.**  
   Gestützt durch Reflexion und multimodale Memory-Arbeiten.

7. **Reflex/Deadlock Recovery sind frühe Kernmodule.**  
   Gestützt durch PokeGym und SIMA-2-Limitierungen.

8. **Screen-only ist primär; Bridge ist Auxiliary/Teacher.**  
   Gestützt durch BALROGs negative Vision-Befunde und standardisierte Schnittstellen aus Cradle/GameWorld.

9. **Gewichte bleiben innerhalb eines Runs eingefroren.**  
   Eine begründete Projektentscheidung aus Reproduzierbarkeit, Safety und generationsweisen Self-Improvement-Ansätzen; Continual Harness bleibt spätere Vergleichsvariante.

10. **Harness und Modell werden getrennt attribuiert.**  
    Gestützt durch PokeAgent, GameWorld und die starke Wirkung modularer Harnesses.