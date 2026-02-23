# LOG650 Proposal

## Project Title
Optimisation of Spare Part Inventory and Refurbishment Planning for MAN Marine Engines in Cruise Ship Operations

## Area
Inventory management and reverse logistics in a maritime supply chain.

This project focuses on inventory management and reverse logistics for repairable spare parts used in MAN marine engines on cruise ships operated by Viking Cruise Lines and managed by Wilhelmsen Ship Management (WSM).

Marine engine spare parts are critical assets. A lack of available parts can cause costly downtime and lost revenue in cruise ship operations. At the same time, holding excessive stock is expensive. This creates a classical logistics trade-off between availability and cost, which is well suited for quantitative optimisation.

---

## Problem Statement
How many critical MAN marine engine spare parts should Wilhelmsen Ship Management keep in central stock in Amsterdam, and when should parts be sent for refurbishment at MAN in order to minimise total logistics cost while maintaining a required service level for cruise ship operations?

The problem is motivated by WSM’s belief that the current spare-part system may be inefficient. They may either hold too much inventory or operate with an inefficient refurbishment process, while still risking running out of critical parts.

---

## Data Foundation
The project will be based on real operational data provided by WSM through Geir Terje Nevøy.

A dedicated data-collection meeting is scheduled where available datasets, system structure, and practical constraints will be reviewed.

Expected data includes (subject to availability):

- Historical failures of MAN engine parts  
- Spare-part usage and replacement history  
- Refurbishment lead times at MAN  
- Current stock levels  
- Costs of new parts and refurbishments  
- Estimated cost of ship downtime  

If some elements are missing, realistic simulation will be used to complement the dataset.

---

## Model
The system will be modelled as a repairable spare-parts inventory system.

### Parameters
- Failure rates of engine parts  
- Repair lead times  
- Inventory holding costs  
- New-part and refurbishment costs  
- Downtime costs  

### Decision Variables
- Number of spare parts to keep in stock  
- When to send parts for refurbishment  
- Replenishment policy  

### Objective (KPI)
Minimise:

Total cost = Inventory cost + Refurbishment cost + Purchase cost + Downtime cost  

Subject to:

Service level ≥ Target value (e.g. 95–99%)

---

## Process
The LOG650 five-step process will be followed:

1. Data Collection  
   Collect real data from WSM and MAN.

2. Assumption Validation  
   Analyse distributions, failure patterns, and lead-time behaviour.

3. Solution Development  
   Build a quantitative model in Python to calculate optimal stock and refurbishment strategies.

4. Solution Testing  
   Perform sensitivity analysis and scenario testing.

5. Implementation  
   Translate results into practical recommendations for Wilhelmsen.

---

## Methods
- Inventory models for repairable spare parts  
- Simulation (Discrete Event / Monte Carlo)  
- Optimisation techniques  
- Machine learning and AI for parameter estimation, simulation, and optimisation  

---

## Role of AI
AI will be used to:

- Analyse WSM datasets  
- Estimate failure and lead-time distributions  
- Implement simulation and optimisation models  
- Generate visualisations and KPIs  

The project team will be responsible for assumptions, model structure, validation, and interpretation of results.

---

## Expected Contribution
The project will provide WSM with:

- A data-driven spare-part planning model  
- Quantified trade-offs between cost and availability  
- A framework that can be reused and updated with new data
