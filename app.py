import streamlit as st
import pandas as pd
import numpy as np

# -------------------------------
# Forestation Planner – GVAN
# -------------------------------

class ForestationPlanner:
    def __init__(self, land_size_ha, soil_type, climate_zone, rainfall_mm,
                 water_source, budget_inr, goal, maintenance_level, preferred_species=None):
        self.land_size = land_size_ha
        self.soil = soil_type
        self.climate = climate_zone
        self.rainfall = rainfall_mm
        self.water_source = water_source
        self.budget_inr = budget_inr
        self.goal = goal
        self.maintenance = maintenance_level
        self.preferred_species = preferred_species

        # Scoring maps (same as before)
        self.soil_score_map = {"Loamy": 1.0, "Sandy": 0.6, "Clay": 0.5, "Rocky": 0.2}
        self.climate_score_map = {"Tropical": 1.0, "Temperate": 0.8, "Arid": 0.4, "Cold": 0.6}
        self.water_score_map = {"River": 1.0, "Well": 0.8, "Seasonal": 0.5, "Rain-fed only": 0.3}
        self.maintenance_cost_factor = {"Low": 0.6, "Medium": 1.0, "High": 1.5}

        # Species database – cost_per_tree in INR (realistic Indian rates)
        # Values are direct INR, not converted from USD
        self.species_db = pd.DataFrame([
            ["Teak (Tectona grandis)", 1200, 2500, "Tropical", "Loamy", 210, "Medium"],
            ["Pine (Pinus roxburghii)", 800, 2000, "Temperate", "Sandy", 100, "Medium"],
            ["Mangrove (Rhizophora)", 1500, 3000, "Tropical", "Clay", 250, "Slow"],
            ["Acacia (Acacia nilotica)", 500, 1500, "Arid", "Sandy", 65, "Fast"],
            ["Oak (Quercus spp.)", 900, 1800, "Temperate", "Loamy", 170, "Slow"],
            ["Eucalyptus (Eucalyptus globulus)", 600, 2000, "Temperate", "Clay", 85, "Fast"],
            ["Cedar (Cedrus deodara)", 1000, 2000, "Cold", "Loamy", 185, "Slow"],
            ["Bamboo (Bambusoideae)", 1000, 3000, "Tropical", "Clay", 125, "Fast"],
        ], columns=["species", "rain_min", "rain_max", "climate", "soil_pref", "cost_per_tree_inr", "growth_rate"])

    def rainfall_score(self):
        if 800 <= self.rainfall <= 2000:
            return 1.0
        elif 500 <= self.rainfall < 800 or 2000 < self.rainfall <= 2500:
            return 0.7
        elif 300 <= self.rainfall < 500:
            return 0.4
        else:
            return 0.2

    def soil_score(self):
        return self.soil_score_map.get(self.soil, 0.3)

    def climate_score(self):
        return self.climate_score_map.get(self.climate, 0.5)

    def water_availability_score(self):
        base = self.water_score_map.get(self.water_source, 0.4)
        if self.rainfall < 600 and self.water_source not in ["River", "Well"]:
            base *= 0.5
        return base

    def overall_suitability(self):
        scores = {
            "soil": self.soil_score(),
            "climate": self.climate_score(),
            "rainfall": self.rainfall_score(),
            "water": self.water_availability_score(),
        }
        weighted = (scores["soil"]*0.3 + scores["climate"]*0.25 +
                    scores["rainfall"]*0.25 + scores["water"]*0.2)
        return weighted * 100

    def recommend_species(self):
        suitable = self.species_db[
            (self.species_db["rain_min"] <= self.rainfall) &
            (self.species_db["rain_max"] >= self.rainfall) &
            (self.species_db["climate"] == self.climate)
        ]
        if suitable.empty:
            suitable = self.species_db[
                (self.species_db["rain_min"] <= self.rainfall) &
                (self.species_db["rain_max"] >= self.rainfall)
            ]
        if suitable.empty:
            return None, 0.0

        def match_score(row):
            if row["soil_pref"] == self.soil:
                return 1.0
            elif row["soil_pref"] == "Loamy" and self.soil in ["Sandy", "Clay"]:
                return 0.7
            else:
                return 0.4
        suitable["soil_match"] = suitable.apply(match_score, axis=1)
        best = suitable.loc[suitable["soil_match"].idxmax()]
        return best["species"], best["soil_match"] * 100

    def optimal_density(self):
        if self.goal == "Timber":
            return 400
        elif self.goal == "Carbon sequestration":
            return 1200
        elif self.goal == "Biodiversity":
            return 800
        elif self.goal == "Erosion control":
            return 1000
        else:
            return 600

    def cost_estimation_inr(self):
        species_name, _ = self.recommend_species()
        if species_name is None:
            cost_per_tree_inr = 165   # default fallback INR
        else:
            cost_per_tree_inr = self.species_db[self.species_db["species"] == species_name]["cost_per_tree_inr"].values[0]

        density = self.optimal_density()
        total_trees = int(self.land_size * density)
        planting_cost = total_trees * cost_per_tree_inr

        # Baseline maintenance: ₹15,000 per hectare per year (Indian context)
        baseline_maintenance_inr = 15000
        maint_factor = self.maintenance_cost_factor.get(self.maintenance, 1.0)
        maint_cost_annual = self.land_size * baseline_maintenance_inr * maint_factor
        total_5yr = planting_cost + (maint_cost_annual * 5)

        return {
            "planting_cost_inr": round(planting_cost, 0),
            "annual_maintenance_inr": round(maint_cost_annual, 0),
            "total_5yr_cost_inr": round(total_5yr, 0),
            "cost_per_tree_inr": round(cost_per_tree_inr, 2),
            "density_trees_per_ha": density,
            "total_trees": total_trees
        }

    def budget_feasibility(self):
        cost = self.cost_estimation_inr()
        total_5yr = cost["total_5yr_cost_inr"]
        if self.budget_inr >= total_5yr:
            return "✅ Budget is sufficient for 5 years."
        elif self.budget_inr >= cost["planting_cost_inr"]:
            return "⚠️ Budget covers planting but not full 5‑year maintenance. Reduce density or increase budget."
        else:
            return "❌ Budget insufficient even for planting. Choose cheaper species or smaller land."

    def success_probability(self):
        suit = self.overall_suitability()
        if suit > 75:
            return "High (≥75%)"
        elif suit > 50:
            return "Medium (50‑74%)"
        else:
            return "Low (<50%)"

    def carbon_sequestration_estimate(self):
        total_trees = self.cost_estimation_inr()["total_trees"]
        yearly_co2 = total_trees * 0.5
        return round(yearly_co2, 0)

    def get_full_report(self):
        suitability = self.overall_suitability()
        species, species_score = self.recommend_species()
        cost = self.cost_estimation_inr()
        budget_status = self.budget_feasibility()
        success_prob = self.success_probability()
        co2 = self.carbon_sequestration_estimate()

        report = f"""
        ## 🌲 Forestation Feasibility Report

        **Overall Suitability Index:** {suitability:.1f}%
        **Predicted Success Probability:** {success_prob}

        ### 🌿 Recommended Species
        - **Best match:** {species if species else "No ideal species – consider soil/water improvements"}
        - **Species‑site matching score:** {species_score:.0f}%

        ### 🌳 Plantation Design
        - **Optimal density:** {cost['density_trees_per_ha']} trees/ha
        - **Total trees for {self.land_size} ha:** {cost['total_trees']} trees
        - **Plantation goal:** {self.goal}

        ### 💰 Cost Breakdown (INR)
        - **Planting cost (trees + labour):** ₹{cost['planting_cost_inr']:,.0f}
        - **Annual maintenance ({self.maintenance} level):** ₹{cost['annual_maintenance_inr']:,.0f}/year
        - **Estimated total over 5 years:** ₹{cost['total_5yr_cost_inr']:,.0f}
        - **Budget feasibility:** {budget_status}

        ### 🌍 Environmental Impact (rough estimate)
        - **Potential carbon sequestration:** ~{co2} tons CO₂ per year

        ### ⚠️ Risk Factors & Recommendations
        """
        risks = []
        if self.soil_score() < 0.6:
            risks.append("- Soil quality is low – consider organic amendment or terracing.")
        if self.rainfall_score() < 0.6:
            risks.append("- Rainfall is suboptimal – supplementary irrigation is critical.")
        if self.water_availability_score() < 0.6:
            risks.append("- Water source reliability is low – plan for drought contingency.")
        if self.maintenance == "Low" and suitability < 60:
            risks.append("- Low maintenance + moderate/low suitability → high failure risk. Increase maintenance to medium.")
        if not risks:
            risks.append("- No major risk detected. Follow standard forestation protocols.")
        report += "\n".join(risks)
        return report


# -------------------------------
# Streamlit UI – All INR
# -------------------------------

st.set_page_config(page_title="Forestation Planner (100% INR)", layout="wide")
st.title("🌳 Forestation Planning & Suitability System")
st.markdown("**All costs and budgets are in Indian Rupees (₹). No currency conversion is used.**")

with st.sidebar:
    st.header("📍 Site & Project Parameters")
    land_size = st.number_input("Land size (hectares)", min_value=0.1, value=10.0, step=0.5)
    soil_type = st.selectbox("Soil type", ["Loamy", "Sandy", "Clay", "Rocky"])
    climate_zone = st.selectbox("Climate zone", ["Tropical", "Temperate", "Arid", "Cold"])
    rainfall = st.number_input("Annual rainfall (mm)", min_value=100, max_value=4000, value=1200, step=50)
    water_source = st.selectbox("Primary water source", ["River", "Well", "Seasonal", "Rain-fed only"])
    budget_inr = st.number_input("Total available budget (₹)", min_value=0, value=500000, step=50000, help="Enter budget in Indian Rupees")
    goal = st.selectbox("Primary plantation goal", ["Timber", "Carbon sequestration", "Biodiversity", "Erosion control"])
    maintenance = st.select_slider("Intended maintenance level", options=["Low", "Medium", "High"])
    preferred = st.text_input("Preferred species (optional)", placeholder="e.g., Teak, Pine")

    run = st.button("🔍 Generate Forestation Plan", type="primary")

if run:
    planner = ForestationPlanner(
        land_size_ha=land_size,
        soil_type=soil_type,
        climate_zone=climate_zone,
        rainfall_mm=rainfall,
        water_source=water_source,
        budget_inr=budget_inr,
        goal=goal,
        maintenance_level=maintenance,
        preferred_species=preferred if preferred else None
    )
    st.success("Report generated based on your inputs and research factors.")
    st.markdown(planner.get_full_report())

    with st.expander("🔍 Detailed factor scores (for reference)"):
        st.write(f"**Soil score:** {planner.soil_score():.2f}")
        st.write(f"**Climate score:** {planner.climate_score():.2f}")
        st.write(f"**Rainfall score:** {planner.rainfall_score():.2f}")
        st.write(f"**Water availability score:** {planner.water_availability_score():.2f}")
        st.write(f"**Overall suitability (0-1):** {planner.overall_suitability()/100:.2f}")

else:
    st.info("👈 Fill in the parameters on the left and click **Generate Forestation Plan**.")