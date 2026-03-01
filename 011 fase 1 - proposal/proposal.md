# LOG650 Proposal

## Project Title

Comparative Analysis of LTSA vs. Non-LTSA Strategies for MAN Marine Engines in Cruise Operations

## Area of Study

This project is situated within supply chain analysis and optimisation, inventory management, and risk and robustness in maritime supply chains.

The study examines strategic maintenance and spare parts management decisions for MAN marine engines installed on cruise vessels operated by Viking Cruise Lines and technically managed by Wilhelmsen Ship Management (WSM).

Marine propulsion engines are mission-critical assets. Their reliability directly affects safety, itinerary stability, customer satisfaction, and revenue generation. Unplanned downtime can result in substantial financial losses and operational disruption.

The strategic choice between operating under a Long-Term Service Agreement (LTSA) with MAN Energy Solutions and managing maintenance independently under a non-LTSA strategy represents a significant operational and financial decision. This project investigates how these two contractual structures influence lifecycle cost, operational availability, and financial risk exposure over time.

## Problem Statement

The central research question guiding this study is:

**How does operating MAN marine engines under an LTSA agreement compared to a non-LTSA strategy affect total lifecycle cost, operational availability, and financial risk exposure in cruise operations?**

The problem evaluates quantifiable outcomes, including:

- Total lifecycle cost  
- Availability percentage  
- Downtime frequency  
- Cost variability  

The purpose of the study is to develop a quantitative decision-support model that enables systematic comparison of the two strategies under uncertainty.

## Model Formulation

The problem is translated into a stochastic lifecycle cost and availability model built on operational and financial data.

### Input Parameters

The model incorporates:

- Failure rate distributions  
- Mean time between failures (MTBF)  
- Repair lead times  
- Spare-part unit costs  
- Inventory holding cost rates  
- Downtime cost per hour  
- Overhaul intervals  
- Refurbishment cycle costs  
- LTSA fee structures  

These parameters describe the technical and economic behaviour of the engine system under both strategies.

### Decision Variables

Depending on scope refinement, decision variables may include:

- Contract strategy selection (LTSA vs. non-LTSA)  
- Spare-part inventory levels  
- Safety stock levels  
- Refurbishment timing  
- Preventive maintenance intervals  

### Objective Function

Minimise:

Expected total lifecycle cost over a defined planning horizon

Subject to:

- Availability ≥ required service level  
- Maintenance and overhaul constraints  
- Contractual conditions  

In addition to expected cost minimisation, the model evaluates variability in cost outcomes to assess financial risk exposure under each strategic alternative.

## Process

The project follows a structured five-step quantitative process.

### 1. Data Collection

Operational data will be obtained from WSM’s Planned Maintenance System and spare-parts management systems, including:

- Maintenance history  
- Overhaul intervals  
- Spare-part consumption patterns  
- Refurbishment cycles  
- Lead times  
- Cost structures  
- Downtime records  

Data quality and completeness will be evaluated before modelling.

### 2. Assumption Validation

Statistical analysis will be conducted to assess:

- Failure distributions  
- Cost behaviour  
- Lead-time characteristics  

Goodness-of-fit testing and exploratory data analysis will ensure modelling assumptions reflect empirical patterns.

### 3. Model Implementation

The model will be implemented in Python.

Due to the stochastic nature of failures and repair processes, Monte Carlo simulation will be used to evaluate lifecycle cost and availability under both LTSA and non-LTSA scenarios.

Simulation is selected because closed-form analytical solutions are not realistic for complex lifecycle systems with uncertainty-driven cost structures.

### 4. Validation and Sensitivity Analysis

Sensitivity analysis will evaluate how changes in key parameters (e.g., failure rates, downtime costs, lead times) influence outcomes.

Scenario testing and limited backtesting using historical data will be conducted to assess robustness.

### 5. Managerial Application

Results will be translated into structured managerial recommendations for Wilhelmsen Ship Management.

The modelling framework is intended to function as a reusable decision-support tool for future vessels, engine types, and contract evaluations.

## Methods

The methodological approach integrates:

- Lifecycle cost analysis  
- Reliability and availability modelling  
- Monte Carlo simulation  
- Sensitivity analysis  
- Scenario comparison  

Statistical estimation techniques will be used to calibrate model parameters from empirical data.

The framework evaluates both expected cost levels and cost variability to assess financial risk allocation between strategies.

## Role of Artificial Intelligence

Artificial intelligence will be used as an analytical support tool.

AI tools may assist with:

- Data preprocessing  
- Statistical parameter estimation  
- Generation of Python simulation code  
- Automation of sensitivity analysis  
- Visualisation of results  

All modelling assumptions, validation procedures, and interpretation of results remain the responsibility of the author. AI is used to enhance analytical efficiency, not to replace critical judgement.

## Expected Contribution

### Academic Contribution

The study contributes to understanding how maintenance contract structures influence lifecycle economics and operational performance in capital-intensive maritime systems.

It integrates stochastic lifecycle modelling with contract-based strategy evaluation in a supply chain context.

### Practical Contribution

The project provides Wilhelmsen Ship Management with:

- A structured quantitative comparison of LTSA and non-LTSA strategies  
- Clear visibility of cost implications and availability trade-offs  
- Assessment of financial risk exposure  

The modelling framework can be reused and adapted for future contract negotiations and strategic evaluations.
