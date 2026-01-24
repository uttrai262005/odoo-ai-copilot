{
    'name': "AI Copilot & Business Automation (Jarvis)", 
    'summary': "Google Gemini Integration. Auto-pilot Sales: AI Analysis, Auto-Quotations, Procurement & Task Assignment.", 
    'description': """
    TRANSFORM YOUR ODOO INTO AN INTELLIGENT SALES MACHINE
    =====================================================
    
    This module integrates Google Gemini AI to automate your daily sales & operation tasks.
    
    KEY FEATURES:
    -------------
    1. 🧠 AI Customer Insights:
       - Instantly analyze customer psychology & budget from a simple description.
       - Generate tailored Sales Strategies & Scripts (Friendly/Professional).
    
    2. 🚀 Auto-Pilot Mode (One-Click Automation):
       - Auto-select optimal Product Combos based on budget.
       - Auto-Create Quotations (Sale Orders).
       - Auto-Check Stock & Create Purchase Orders for missing items.
       - Auto-Assign "Packaging" Tasks to the Warehouse team.
       
    3. 💌 Smart Content Generation:
       - Generate personalized Gift Card messages.
       - Create QR Codes for order tracking.
       
    PERFECT FOR: E-commerce, Retail, Handmade, and Custom Service businesses.
    """,
    'author': "Nguyen Dinh Truc", 
    'website': "https://github.com/uttrai262005", 
    
    'category': 'Sales/CRM',
    'version': '19.0.1.0.0',    
    # LICENSE 
    'license': 'OPL-1', 
    'price': 19.00,
    'currency': 'USD',
    
    'depends': ['base', 'crm', 'sale_management', 'purchase', 'project', 'stock'], 
    
    'data': [
        'views/crm_ai_view.xml',
    ],
    
    'images': ['static/description/banner.png'],
    
    'installable': True,
    'application': True,
}