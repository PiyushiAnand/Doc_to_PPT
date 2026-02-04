import os
import requests
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_CONNECTOR
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE

# ---------------------------------------------------------
# CONFIGURATION (MATCHING SAMPLE PPT STYLE)
# ---------------------------------------------------------
# Sample uses a deep corporate blue/teal. Let's match it.
THEME_COLOR = RGBColor(0, 75, 120)    # Deep Corporate Blue
TEXT_COLOR = RGBColor(50, 50, 50)     # Soft Black for readability
ACCENT_COLOR = RGBColor(200, 200, 200) # Light Grey for divider lines
FOOTER_TEXT = "Strictly Private & Confidential – Prepared by Kelp M&A Team"
FONT_NAME = 'Calibri'

def download_image(query, filename="temp_img.jpg"):
    """Downloads a generic stock image with browser headers."""
    if not query: return None
    safe_query = query.replace(" ", ",").lower()
    url = f"https://loremflickr.com/800/600/{safe_query}"
    print(f"   [Img] Downloading: {url}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200 and len(response.content) > 1000:
            with open(filename, 'wb') as f:
                f.write(response.content)
            return filename
    except Exception as e:
        print(f"   [Warning] Image download error: {e}")
    return None

def apply_branding(slide, slide_title):
    """Adds the Header, Divider Line, and Footer to match the sample."""
    
    # 1. Title
    title_shape = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(9), Inches(0.8))
    title_tf = title_shape.text_frame
    title_p = title_tf.paragraphs[0]
    title_p.text = slide_title
    title_p.font.name = FONT_NAME
    title_p.font.bold = True
    title_p.font.size = Pt(24)
    title_p.font.color.rgb = THEME_COLOR
    
    # 2. Divider Line (The "Investement Bank" Horizontal Rule)
    #    Draws a line right under the title from left to right margin
    line = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT, 
        Inches(0.5), Inches(1.1), Inches(9.5), Inches(1.1)
    )
    line.line.color.rgb = ACCENT_COLOR
    line.line.width = Pt(1.5)

    # 3. Footer
    footer_box = slide.shapes.add_textbox(Inches(0.5), Inches(7.1), Inches(9), Inches(0.4))
    tf = footer_box.text_frame
    p = tf.paragraphs[0]
    p.text = FOOTER_TEXT
    p.font.name = FONT_NAME
    p.font.size = Pt(9)
    p.font.color.rgb = RGBColor(150, 150, 150)
    p.alignment = PP_ALIGN.CENTER

def create_native_chart(slide, chart_data_dict):
    if not chart_data_dict or not chart_data_dict.get("values"): return 

    chart_data = CategoryChartData()
    chart_data.categories = chart_data_dict.get("labels", [])
    chart_data.add_series('Series 1', chart_data_dict.get("values", []))
    
    # Chart Position: Right side, aligned with text top
    x, y, cx, cy = Inches(5.8), Inches(1.5), Inches(3.8), Inches(3.0)
    try:
        chart = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, x, y, cx, cy, chart_data).chart
        chart.chart_title.text_frame.text = chart_data_dict.get("title", "Financials")
        chart.chart_title.text_frame.paragraphs[0].font.size = Pt(12)
        chart.chart_title.text_frame.paragraphs[0].font.name = FONT_NAME
    except: pass

def generate_styled_ppt(ppt_data, output_file):
    prs = Presentation()
    slides_list = ppt_data.get("slides", [])
    
    for i, slide_content in enumerate(slides_list):
        # Use BLANK layout (index 6) for total control
        slide = prs.slides.add_slide(prs.slide_layouts[6]) 
        
        # Apply the Header/Footer/Line style
        apply_branding(slide, slide_content.get("title", "Slide"))
        
        # ---------------------------------------------------------
        # CONTENT COLUMN (Left Side)
        # ---------------------------------------------------------
        # Positioned nicely under the divider line
        content_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.4), Inches(5), Inches(5))
        tf = content_box.text_frame
        tf.word_wrap = True
        
        bullets = slide_content.get("bullets", [])
        for index, bullet in enumerate(bullets):
            p = tf.add_paragraph() # Always add new for control
            
            # Text Processing
            raw_text = bullet["text"] if isinstance(bullet, dict) else str(bullet)
            p.text = "• " + raw_text
            
            # Styling
            p.font.name = FONT_NAME
            p.font.size = Pt(14)
            p.font.color.rgb = TEXT_COLOR
            p.space_after = Pt(10) # Clean spacing between items
            p.level = 0

        # ---------------------------------------------------------
        # VISUALS COLUMN (Right Side)
        # ---------------------------------------------------------
        chart_data = slide_content.get("chart_data")
        has_chart = chart_data and chart_data.get("values") and len(chart_data.get("values")) > 0

        if has_chart:
             create_native_chart(slide, chart_data)
        elif slide_content.get("image_query"):
             img_filename = f"temp_img_{i}.jpg"
             img_path = download_image(slide_content["image_query"], img_filename)
             if img_path:
                 try:
                    # Place image on the right, aligned with text
                    slide.shapes.add_picture(img_path, Inches(5.8), Inches(1.5), width=Inches(3.8))
                 except Exception as e:
                    print(f"   [Error] Add picture failed: {e}")

    prs.save(output_file)
    print(f"PPT Saved: {output_file}")
    
    # Cleanup
    for i in range(len(slides_list)):
        if os.path.exists(f"temp_img_{i}.jpg"):
            try: os.remove(f"temp_img_{i}.jpg")
            except: pass