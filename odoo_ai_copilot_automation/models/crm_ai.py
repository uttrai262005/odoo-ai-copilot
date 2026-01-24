# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import google.generativeai as genai
import requests
import re
import urllib.parse

class CrmLeadAI(models.Model):
    _inherit = 'crm.lead'

    # --- FIELDS (ENGLISH) ---
    ai_summary = fields.Text(string="AI Analysis")
    ai_score = fields.Integer(string="Potential Score")
    ai_budget = fields.Float(string="Est. Budget (AI)")
    
    ai_gift_message = fields.Text(string="Gift Message")
    ai_reply_friendly = fields.Text(string="Friendly Reply")
    ai_reply_professional = fields.Text(string="Professional Reply")
    ai_strategy = fields.Text(string="Sales Strategy")
    
    qr_code_html = fields.Html(string="QR Code", compute="_compute_qr_code")

    # --- QR CODE GENERATION ---
    @api.depends('name', 'contact_name', 'phone')
    def _compute_qr_code(self):
        for record in self:
            # Data encoding for QR
            customer_name = record.contact_name or record.name or "Guest"
            phone = record.phone or "N/A"
            raw_content = f"Customer: {customer_name} | Phone: {phone} | Lead ID: {record.id}"
            
            # URL Encoding
            safe_content = urllib.parse.quote(raw_content)
            img_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={safe_content}&charset-source=UTF-8"
            
            # Render HTML
            record.qr_code_html = f'<img src="{img_url}" alt="QR Code" style="border:1px solid #ccc; padding:5px;"/>'

    # --- GET PRODUCT LIST FOR AI CONTEXT ---
    def get_product_list_for_ai(self):
        # Fetch active products
        products = self.env['product.product'].search([
            ('sale_ok', '=', True), 
            ('active', '=', True)
        ], order='list_price asc', limit=50) 
        
        menu_str = ""
        for p in products:
            # Format: [ID:12] - Product Name (Price: 100)
            menu_str += f"[ID:{p.id}] - {p.name} (Price: {int(p.list_price)})\n"
            
        return menu_str if menu_str else "Inventory is empty."

    # --- MAIN AI ACTION ---
    def action_ask_ai(self):
        # RECOMMENDATION: Move API Key to System Parameters in production
        MY_API_KEY = "AIzaSyBk8iWXuMlYjrrinzGqUWz_v1bKCtiA4JI" 
        MODEL_NAME = 'gemini-2.5-flash' 
        
        try:
            genai.configure(api_key=MY_API_KEY)
            model = genai.GenerativeModel(MODEL_NAME) 
            product_menu = self.get_product_list_for_ai()

            for record in self:
                # Prepare input data
                customer_info = f"Name: {record.contact_name}, Requirement: {record.description}"
                
                # --- ENGLISH PROMPT ENGINEERING ---
                prompt = f"""
                You are a Professional Sales Assistant for 'Decharmix' - A sophisticated Handmade Accessories Brand.
                Slogan: "Wrapping love in every knot".
                
                1. CURRENT INVENTORY (ID - Name - Price):
                {product_menu}
                --------------------
                2. CUSTOMER INFO: {customer_info}
                --------------------
                YOUR STRATEGIC MISSION:
                - Step 1: Estimate Budget. If not specified, guess based on the requested items context.
                - Step 2: Select a Product Combo.
                  + PRIORITY 1: Match the core requirement.
                  + PRIORITY 2 (UPSELL): Always try to add a "Gift Box" or "Card" if it's a gift and fits the budget.
                - Step 3: Urgency handling. If urgent, pick ready-made items.
                
                RULES FOR PRODUCT SELECTION:
                - Do NOT exceed the estimated budget (unless < 10% over for a perfect match).
                - Do NOT hallucinate product IDs. Only use IDs from the INVENTORY list above.
                
                RESPONSE FORMAT (STRICTLY FOLLOW THIS):
                [BUDGET]: (Number only, e.g., 500000)
                [SCORE]: (Integer 0-100, based on lead potential)
                [ANALYSIS]: (Short analysis in English: Customer style, why this combo? Upsell opportunity?)
                [CHAT_REPLY]: (A friendly, casual reply message for chat apps like Zalo/WhatsApp. Tone: Gen Z, cute, use emojis 🌸✨)
                [SALES_PITCH]: (A professional closing message, listing the selected combo and total price. Call to action.)
                [GIFT_MESSAGE]: (A short, deep, meaningful wish for the gift card. Leave "..." for the recipient's name)
                [STRATEGY]: (Internal note: Upsell strategy / Psychological trigger / Bundle logic...)
                
                [ORDER_LIST]:
                ID: QUANTITY
                ID: QUANTITY
                ...
                """
                
                # Call Gemini AI
                response = model.generate_content(prompt)
                text = response.text
                record.ai_summary = text 

                # --- REGEX PARSING (UPDATED FOR ENGLISH TAGS) ---
                score_match = re.search(r'\[SCORE\]:\s*(\d+)', text)
                budget_match = re.search(r'\[BUDGET\]:\s*([\d]+)', text)
                cart_match = re.search(r'\[ORDER_LIST\]:([\s\S]*)', text)
                
                # Parse Text Blocks
                zalo1_match = re.search(r'\[CHAT_REPLY\]:([\s\S]*)\[SALES_PITCH\]', text)
                zalo2_match = re.search(r'\[SALES_PITCH\]:([\s\S]*)\[GIFT_MESSAGE\]', text)
                msg_match = re.search(r'\[GIFT_MESSAGE\]:([\s\S]*)\[STRATEGY\]', text)
                strat_match = re.search(r'\[STRATEGY\]:([\s\S]*)', text) 
                
                # Assign Values
                if score_match: record.ai_score = int(score_match.group(1))
                if budget_match: 
                    try: record.ai_budget = float(budget_match.group(1))
                    except: pass
                
                if zalo1_match: record.ai_reply_friendly = zalo1_match.group(1).strip()
                if zalo2_match: record.ai_reply_professional = zalo2_match.group(1).strip()
                if msg_match: record.ai_gift_message = msg_match.group(1).strip()
                if strat_match: record.ai_strategy = strat_match.group(1).strip()

                # LOGIC: CREATE QUOTATION + AUTO PILOT
                created_order_name = False
                if record.ai_score > 0 and cart_match:
                    cart_text = cart_match.group(1).strip()
                    created_order_name = self.create_quotation_combo(record, cart_text)

                # NOTIFICATION
                msg_notify = f"Quotation Created & Stock Checked: {created_order_name}" if created_order_name else "AI Analysis Completed (No Order Created)."
                return {
                    'type': 'ir.actions.client', 
                    'tag': 'display_notification', 
                    'params': {
                        'title': 'JARVIS AUTO-PILOT', 
                        'message': msg_notify, 
                        'type': 'success', 
                        'sticky': False
                    }
                }

        except Exception as e:
            raise UserError(f"AI Error: {str(e)}")

    # --- PRINT ACTION ---
    def action_print_gift_card(self):
        return self.env.ref('nhom2_ai_copilot.action_report_gift_card').report_action(self)

    # --- ORDER CREATION LOGIC ---
    def create_quotation_combo(self, lead, cart_text):
        # Create or Get Customer
        partner_name = lead.contact_name or lead.name
        partner = lead.partner_id or self.env['res.partner'].create({'name': partner_name})
        lead.partner_id = partner.id
        
        order_lines = []
        
        # Parse Line by Line
        for line in cart_text.split('\n'):
            # Regex to find numbers. Expected format: "ID: 99, Qty: 2" or "99: 2"
            nums = re.findall(r'\d+', line)
            
            if len(nums) >= 2:
                try:
                    p_id = int(nums[0]) # First number is ID
                    qty = int(nums[1])  # Second number is Qty
                    
                    product = self.env['product.product'].browse(p_id)
                    if product.exists():
                        order_lines.append((0, 0, {
                            'product_id': p_id,
                            'product_uom_qty': qty,
                            'price_unit': product.list_price
                        }))
                except: continue
        
        # Fallback Product if list is empty or invalid
        if not order_lines:
            default_prod = self.env['product.product'].search([('name', '=', 'Handmade Gift Box (Demo)')], limit=1) or \
                           self.env['product.product'].create({'name': 'Handmade Gift Box (Demo)', 'list_price': 20.0, 'type': 'service'})
            order_lines.append((0, 0, {'product_id': default_prod.id, 'product_uom_qty': 1, 'price_unit': 20.0}))

        # 1. CREATE SALE ORDER
        order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'opportunity_id': lead.id,
            'order_line': order_lines
        })

        # 2. TRIGGER AUTO-PILOT
        self.run_auto_pilot(order)
        
        return order.name

    # --- AUTO PILOT LOGIC (PROCUREMENT & TASK) ---
    def run_auto_pilot(self, order):
        # Check Stock
        missing_products = []
        for line in order.order_line:
            if line.product_id.type == 'product':
                if line.product_id.qty_available < line.product_uom_qty:
                    missing_products.append(line)

        # A. Auto-Create Purchase Order (If stock low)
        if missing_products:
            supplier = self.env['res.partner'].search([('name', '=', 'Material Supplier')], limit=1) or \
                       self.env['res.partner'].create({'name': 'Material Supplier'})
            po_lines = []
            for line in missing_products:
                qty_buy = line.product_uom_qty - line.product_id.qty_available + 5 # Safety stock
                po_lines.append((0, 0, {
                    'product_id': line.product_id.id, 
                    'product_qty': qty_buy, 
                    'price_unit': line.product_id.standard_price or 1.0, 
                    'date_planned': fields.Datetime.now(), 
                    'product_uom': line.product_uom.id
                }))
            self.env['purchase.order'].create({
                'partner_id': supplier.id, 
                'order_line': po_lines, 
                'origin': f"Auto from {order.name}"
            })

        # B. Auto-Create Project Task (Packaging)
        project = self.env['project.project'].search([('name', '=', 'Handmade Workshop')], limit=1) or \
                  self.env['project.project'].create({'name': 'Handmade Workshop'})
        
        task_desc = f"Order Ref: {order.name}\nPacking List:\n"
        for line in order.order_line: 
            task_desc += f"- {line.product_uom_qty} x {line.product_id.name}\n"
            
        self.env['project.task'].create({
            'name': f"🎁 Pack Gift for {order.name}", 
            'project_id': project.id, 
            'description': task_desc, 
            'user_ids': [(4, self.env.user.id)], 
            'date_deadline': fields.Date.today()
        })