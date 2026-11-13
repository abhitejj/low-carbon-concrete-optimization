import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def create_deck():
    prs = Presentation()
    # 16:9 widescreen dimensions
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6] # blank layout

    # Color definitions
    NAVY = RGBColor(15, 23, 42)        # #0F172A
    BLUE = RGBColor(37, 99, 235)       # #2563EB
    CHARCOAL = RGBColor(51, 65, 85)    # #334155
    MUTED = RGBColor(100, 116, 139)    # #64748B
    BG_CARD = RGBColor(248, 250, 252)  # #F8FAFC
    BORDER = RGBColor(203, 213, 225)   # #CBD5E1
    WHITE = RGBColor(255, 255, 255)
    GREEN = RGBColor(22, 163, 74)      # #16A34A
    RED = RGBColor(220, 38, 38)        # #DC2626

    def add_header(slide, badge_text, title_text):
        # Badge
        badge = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.35))
        tf_b = badge.text_frame
        tf_b.word_wrap = True
        tf_b.margin_left = tf_b.margin_top = tf_b.margin_right = tf_b.margin_bottom = 0
        p_b = tf_b.paragraphs[0]
        p_b.text = badge_text.upper()
        p_b.font.size = Pt(10)
        p_b.font.bold = True
        p_b.font.color.rgb = BLUE

        # Title
        title = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11.7), Inches(0.7))
        tf_t = title.text_frame
        tf_t.word_wrap = True
        tf_t.margin_left = tf_t.margin_top = tf_t.margin_right = tf_t.margin_bottom = 0
        p_t = tf_t.paragraphs[0]
        p_t.text = title_text
        p_t.font.size = Pt(24)
        p_t.font.bold = True
        p_t.font.color.rgb = NAVY

    def add_card(slide, left, top, width, height, title, items, border_color=BORDER, bg_color=BG_CARD):
        # Background shape
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = bg_color
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1.2)

        # Content box inside
        pad = Inches(0.2)
        tb = slide.shapes.add_textbox(left + pad, top + pad, width - 2*pad, height - 2*pad)
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        # Title
        p0 = tf.paragraphs[0]
        p0.text = title
        p0.font.size = Pt(14)
        p0.font.bold = True
        p0.font.color.rgb = NAVY
        p0.space_after = Pt(8)

        # Items
        for item in items:
            p = tf.add_paragraph()
            p.space_after = Pt(6)
            if isinstance(item, tuple):
                lead, text = item
                run1 = p.add_run()
                run1.text = lead + " "
                run1.font.bold = True
                run1.font.size = Pt(11)
                run1.font.color.rgb = CHARCOAL

                run2 = p.add_run()
                run2.text = text
                run2.font.bold = False
                run2.font.size = Pt(11)
                run2.font.color.rgb = CHARCOAL
            else:
                run = p.add_run()
                run.text = item
                run.font.size = Pt(11)
                run.font.color.rgb = CHARCOAL

    # ==================== SLIDE 1: Title Slide ====================
    s1 = prs.slides.add_slide(blank_layout)
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = NAVY
    bg1.line.fill.background()

    # Title box
    tb1 = s1.shapes.add_textbox(Inches(1.2), Inches(1.8), Inches(10.9), Inches(3.5))
    tf1 = tb1.text_frame
    tf1.word_wrap = True

    p_badge = tf1.paragraphs[0]
    p_badge.text = "CIVIL ENGINEERING RESEARCH • MESS 2026 TERM PROJECT"
    p_badge.font.size = Pt(12)
    p_badge.font.bold = True
    p_badge.font.color.rgb = RGBColor(96, 165, 250) # Light blue
    p_badge.space_after = Pt(14)

    p_title = tf1.add_paragraph()
    p_title.text = "Greener Concrete Without the Rust"
    p_title.font.size = Pt(36)
    p_title.font.bold = True
    p_title.font.color.rgb = WHITE
    p_title.space_after = Pt(10)

    p_sub = tf1.add_paragraph()
    p_sub.text = "Constrained Lifecycle Optimization Under 11-Year Natural Carbonation Kinetics & Compressive Strength Demands"
    p_sub.font.size = Pt(18)
    p_sub.font.color.rgb = RGBColor(203, 213, 225)
    p_sub.space_after = Pt(28)

    p_auth = tf1.add_paragraph()
    p_auth.text = "Abhitej Singh Bhullar (Roll No. 23110009)\nDepartment of Civil Engineering | Modeling of Earth System and Sustainability"
    p_auth.font.size = Pt(13)
    p_auth.font.color.rgb = RGBColor(148, 163, 184)

    # ==================== SLIDE 2: The Core Dilemma ====================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "The Earth System Paradox", "The Decarbonization vs. Durability Paradox")
    
    # Left Column: Cards
    add_card(s2, Inches(0.8), Inches(1.6), Inches(5.6), Inches(2.4),
             "The Green Mandate (Cutting Clinker)", [
                 ("7–8% Global CO2:", "Cement clinker calcination is a massive greenhouse driver."),
                 ("Industrial SCMs:", "Fly Ash and Slag replace clinker to cut embodied carbon."),
                 ("The Target:", "Reduce carbon footprint while meeting 28-day structural strength.")
             ], border_color=BLUE)

    add_card(s2, Inches(0.8), Inches(4.3), Inches(5.6), Inches(2.5),
             "The Durability Catch (Chemical Shield)", [
                 ("Alkaline Armor:", "Hydrating cement creates Ca(OH)2, keeping pore pH > 12.5."),
                 ("Passivation:", "High alkalinity forms a microscopic passive oxide film on steel rebar."),
                 ("Carbonation Threat:", "SCMs deplete Ca(OH)2; atmospheric CO2 neutralizes concrete (pH < 9.0), causing rebar corrosion.")
             ], border_color=RED)

    # Right Column: Diagram
    if os.path.exists("diagram_carbonation_mechanism.png"):
        s2.shapes.add_picture("diagram_carbonation_mechanism.png", Inches(6.7), Inches(1.75), Inches(5.8), Inches(4.8))

    # ==================== SLIDE 3: 11-Year Field Reality Check ====================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "Decade-Long Empirical Ground Truth", "11-Year Field Weathering: Lab Myths vs. Reality")

    add_card(s3, Inches(0.8), Inches(1.6), Inches(5.4), Inches(2.5),
             "Chennai Field Campaign (11 Years, 45 Mixes)", [
                 ("Real Exposure:", "45 mixtures exposed up to 11.5 years with 353 phenolphthalein tests."),
                 ("Lab vs. Reality:", "Accelerated lab tests (1–4% CO2) distort pore structure; natural field exposure captures true long-term kinetics."),
                 ("Rigorous Hierarchy:", "Strict separation of Tier 1 measured data from Tier 2 models and Tier 3 codes.")
             ], border_color=BLUE)

    add_card(s3, Inches(0.8), Inches(4.35), Inches(5.4), Inches(2.5),
             "Microclimate Physics: Monsoon Pore-Blocking", [
                 ("Sheltered (Indoors):", "Dry convective pores drive rapid continuous CO2 diffusion."),
                 ("Unsheltered (Outdoors):", "Monsoon rain fills pores; CO2 diffusion in water is 10,000x slower (D_aq ≈ 10^-4 D_gas)."),
                 ("The Result:", "26% to 30% empirical carbonation rate attenuation outdoors!")
             ], border_color=GREEN)

    if os.path.exists("fig1_carbonation_kinetics_by_condition.png"):
        s3.shapes.add_picture("fig1_carbonation_kinetics_by_condition.png", Inches(6.5), Inches(1.9), Inches(6.1), Inches(4.5))

    # ==================== SLIDE 4: Air Voids & SCM Kinetics ====================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "Predictive Physical Modeling", "The Air-Void Breakthrough & SCM Kinetic Divergence")

    add_card(s4, Inches(0.8), Inches(1.6), Inches(5.4), Inches(2.5),
             "The Entrapped Air Void Trap", [
                 ("The Mystery:", "Raw compressive strength vs. w/b showed R² = 0.07 (complete breakdown)."),
                 ("The Cause:", "Stiff low-w/b batches without plasticizer trapped up to 6.6% air voids."),
                 ("The Breakthrough:", "Normalizing air voids (-4.35 MPa/% air) restored Bolomey linear trend to R² = 0.73.")
             ], border_color=BLUE)

    add_card(s4, Inches(0.8), Inches(4.35), Inches(5.4), Inches(2.5),
             "The Kinetic Race: Fly Ash vs. Slag", [
                 ("2.17x Kinetic Speedup:", "Fly ash accelerates carbonation 2.17x faster than slag in log space."),
                 ("+10% Fly Ash:", "Increases carbonation rate by +28.7% by consuming Portlandite."),
                 ("+10% Slag:", "Increases rate by only +12.3% while refining pore microstructure.")
             ], border_color=RED)

    if os.path.exists("fig4_strength_verification_abrams_air.png"):
        s4.shapes.add_picture("fig4_strength_verification_abrams_air.png", Inches(6.5), Inches(1.9), Inches(6.1), Inches(4.5))

    # ==================== SLIDE 5: The Sweet Spot (Optimization) ====================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "Constrained Lifecycle Optimization", "Balancing Strength, Durability & Carbon")

    add_card(s5, Inches(0.8), Inches(1.6), Inches(5.6), Inches(2.5),
             "The Optimization Formulation", [
                 ("Objective:", "Minimize Net Lifecycle GWP (Embodied carbon minus 50-year stoichiometric CO2 uptake)."),
                 ("Strength Constraint:", "Clear design demand plus codified IS 10262 buffer (+8.25 MPa)."),
                 ("Durability Constraint:", "Ensure 50-year carbonation front never depassivates rebar, even under +15% kinetic uncertainty.")
             ], border_color=BLUE)

    add_card(s5, Inches(0.8), Inches(4.35), Inches(5.6), Inches(2.5),
             "The Synergistic Winner (C35/45, 30 mm Cover)", [
                 ("Proportions:", "w/b = 0.45, B = 280 kg/m³, 24% Fly Ash + 26% Slag."),
                 ("Slag's Role:", "Provides essential alkaline buffering to stop rebar corrosion."),
                 ("Fly Ash's Role:", "Drives maximum carbon reduction at minimum cost."),
                 ("Net Carbon Footprint:", "133.4 kg CO2e/m³ (Saving 14.1 kg/m³ over standard slag mix).")
             ], border_color=GREEN)

    if os.path.exists("fig3_optimization_tradeoff_landscape.png"):
        s5.shapes.add_picture("fig3_optimization_tradeoff_landscape.png", Inches(6.7), Inches(1.85), Inches(5.8), Inches(4.8))

    # ==================== SLIDE 6: Key Findings & Pareto Frontier ====================
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "Results & Pareto Dynamics", "Key Impact Numbers: Savings, Traps & Dividends")

    add_card(s6, Inches(0.8), Inches(1.6), Inches(5.4), Inches(1.65),
             "-14.1 kg CO2e/m³ Net Carbon Savings", [
                 ("79% from Binder Reduction:", "Lowering binder from 310 to 280 kg/m³."),
                 ("21% from SCM Blending:", "Pairing slag with fly ash avoids pure-mix penalties.")
             ], border_color=GREEN)

    add_card(s6, Inches(0.8), Inches(3.45), Inches(5.4), Inches(1.65),
             "The 25 mm Uncertainty Trap (+16.5% Penalty)", [
                 ("Nominal vs. Buffered:", "Mix C39 looks best nominally, but +15% kinetic uncertainty eliminates it (d50 = 26.0 > 25 mm)."),
                 ("Cost of Safety:", "Forces specifiers back to C23, imposing a +16.5% carbon penalty.")
             ], border_color=RED)

    add_card(s6, Inches(0.8), Inches(5.3), Inches(5.4), Inches(1.6),
             "The Cover Dividend: 0.41 kg/m³ Saved per mm", [
                 ("Design Leverage:", "Every additional mm of cover allows replacing expensive slag with greener fly ash.")
             ], border_color=BLUE)

    if os.path.exists("fig6_pareto_carbon_vs_strength.png"):
        s6.shapes.add_picture("fig6_pareto_carbon_vs_strength.png", Inches(6.5), Inches(1.9), Inches(6.1), Inches(4.6))

    # ==================== SLIDE 7: Practical Takeaways ====================
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "Specification Guidelines", "Practical Rules for Structural Engineers")

    card_w = Inches(3.6)
    card_h = Inches(4.8)
    top_pos = Inches(1.8)

    # Card 1
    add_card(s7, Inches(0.8), top_pos, card_w, card_h,
             "01 | Never Fly Solo", [
                 ("The Rule:", "Never use high fly ash in isolation for carbonation-sensitive structures."),
                 ("The Physics:", "Fly ash voraciously consumes Portlandite and creates slow early microstructure."),
                 ("The Solution:", "Always pair fly ash with blast-furnace slag (GGBS) to maintain the alkaline passivating shield.")
             ], border_color=BLUE)

    # Card 2
    add_card(s7, Inches(4.8), top_pos, card_w, card_h,
             "02 | Add 5 mm of Cover", [
                 ("The Rule:", "Increase rebar cover from 25 mm to 30 mm in indoor/sheltered environments."),
                 ("The Dividend:", "Saves an average of 0.41 kg CO2e/m³ per mm by unlocking high fly ash replacement."),
                 ("Economic Reality:", "An extra 5 mm of cover is the cheapest, highest-leverage way to build green.")
             ], border_color=GREEN)

    # Card 3
    add_card(s7, Inches(8.8), top_pos, card_w, card_h,
             "03 | Control Air Voids", [
                 ("The Rule:", "Enforce strict on-site compaction and use modern PCE superplasticizers with defoamers."),
                 ("The Risk:", "At w/b = 0.45, every 1% entrapped air destroys 4.35 MPa of compressive strength."),
                 ("Compaction Limit:", "Air must stay <= 2.11% before safety margins bind.")
             ], border_color=RED)

    # Save presentation
    prs.save("MESS_Presentation_Visual.pptx")
    prs.save("MESS_Presentation_Bhullar.pptx")
    print("Successfully built visual presentations with embedded diagrams!")

if __name__ == "__main__":
    create_deck()
