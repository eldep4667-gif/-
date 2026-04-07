"""
NEXUS Trading Platform - PDF Report Generator
Generates professional analysis reports in PDF format
"""

import os
import tempfile
from datetime import datetime


class ReportGenerator:
    """
    Generates professional PDF trading analysis reports.
    Uses reportlab library for PDF generation.
    """

    def __init__(self, df, ta, pattern_detector, schools, signal, symbol: str):
        self.df      = df
        self.ta      = ta
        self.pd_     = pattern_detector
        self.schools = schools
        self.signal  = signal
        self.symbol  = symbol
        self.report_dir = os.path.join(tempfile.gettempdir(), "nexus_reports")
        os.makedirs(self.report_dir, exist_ok=True)

    def generate(self) -> str:
        """Generate and return path to the PDF report."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                            Table, TableStyle, HRFlowable)
            from reportlab.lib.enums import TA_CENTER, TA_LEFT

            # ── File Path ─────────────────────────────────────────
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath  = os.path.join(self.report_dir, f'nexus_analysis_{timestamp}.pdf')

            # ── Colors ────────────────────────────────────────────
            dark_bg    = colors.HexColor('#080b14')
            accent     = colors.HexColor('#00d4aa')
            text_light = colors.HexColor('#e2e8f0')
            text_muted = colors.HexColor('#8892a4')
            bull_green = colors.HexColor('#00d4aa')
            bear_red   = colors.HexColor('#ff4757')

            # ── Document Setup ────────────────────────────────────
            doc = SimpleDocTemplate(
                filepath, pagesize=A4,
                rightMargin=2*cm, leftMargin=2*cm,
                topMargin=2*cm, bottomMargin=2*cm
            )

            styles = getSampleStyleSheet()
            story  = []

            # ── Custom Styles ─────────────────────────────────────
            title_style = ParagraphStyle(
                'Title', parent=styles['Title'],
                fontSize=28, textColor=accent,
                spaceAfter=4, alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            subtitle_style = ParagraphStyle(
                'Subtitle', parent=styles['Normal'],
                fontSize=11, textColor=text_muted,
                spaceAfter=20, alignment=TA_CENTER
            )
            h2_style = ParagraphStyle(
                'H2', parent=styles['Heading2'],
                fontSize=14, textColor=accent,
                spaceBefore=16, spaceAfter=8,
                fontName='Helvetica-Bold'
            )
            body_style = ParagraphStyle(
                'Body', parent=styles['Normal'],
                fontSize=10, textColor=colors.HexColor('#2d3748'),
                spaceAfter=6, leading=16
            )
            signal_style_map = {
                'BUY':  colors.HexColor('#00d4aa'),
                'SELL': colors.HexColor('#ff4757'),
                'WAIT': colors.HexColor('#f39c12')
            }

            # ── Header ────────────────────────────────────────────
            story.append(Paragraph("⚡ NEXUS TRADING INTELLIGENCE", title_style))
            story.append(Paragraph("Professional Market Analysis Report", subtitle_style))
            story.append(HRFlowable(width="100%", thickness=1, color=accent))
            story.append(Spacer(1, 0.3*cm))

            # ── Meta Info ─────────────────────────────────────────
            current = self.df['close'].iloc[-1]
            change  = ((current - self.df['close'].iloc[-2]) / self.df['close'].iloc[-2]) * 100

            meta_data = [
                ['Instrument', self.symbol, 'Generated', datetime.now().strftime('%Y-%m-%d %H:%M UTC')],
                ['Current Price', f'{current:.5f}', '24h Change', f'{"+" if change>0 else ""}{change:.2f}%'],
                ['Data Points', f'{len(self.df):,}', 'Report Version', '2.0.0'],
            ]
            meta_table = Table(meta_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
            meta_table.setStyle(TableStyle([
                ('FONTNAME',    (0,0), (-1,-1), 'Helvetica'),
                ('FONTSIZE',    (0,0), (-1,-1), 9),
                ('TEXTCOLOR',   (0,0), (0,-1), colors.HexColor('#4a5568')),
                ('TEXTCOLOR',   (2,0), (2,-1), colors.HexColor('#4a5568')),
                ('TEXTCOLOR',   (1,0), (1,-1), colors.HexColor('#1a202c')),
                ('TEXTCOLOR',   (3,0), (3,-1), colors.HexColor('#1a202c')),
                ('FONTNAME',    (1,0), (1,-1), 'Helvetica-Bold'),
                ('FONTNAME',    (3,0), (3,-1), 'Helvetica-Bold'),
                ('GRID',        (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                ('BACKGROUND',  (0,0), (-1,-1), colors.HexColor('#f8fafc')),
                ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.HexColor('#f8fafc'), colors.white]),
                ('PADDING',     (0,0), (-1,-1), 6),
            ]))
            story.append(meta_table)
            story.append(Spacer(1, 0.5*cm))

            # ── AI Signal ─────────────────────────────────────────
            story.append(Paragraph("AI TRADING SIGNAL", h2_style))
            action  = self.signal.get('action', 'WAIT')
            sig_col = signal_style_map.get(action, colors.HexColor('#f39c12'))

            signal_data = [
                ['RECOMMENDATION', action, 'CONFIDENCE', f"{self.signal.get('confidence', 0):.0f}%"],
                ['ENTRY PRICE', f"{self.signal.get('entry', current):.5f}",
                 'STOP LOSS', f"{self.signal.get('stop_loss', 0):.5f}"],
                ['TAKE PROFIT', f"{self.signal.get('take_profit', self.signal.get('take_profit_1', 0)):.5f}",
                 'TAKE PROFIT 2', f"{self.signal.get('take_profit_2', self.signal.get('take_profit', 0)):.5f}"],
                ['RISK/REWARD', f"1 : {self.signal.get('risk_reward', 2):.1f}",
                 'SIGNAL BASIS', 'Multi-factor AI Analysis'],
            ]
            sig_table = Table(signal_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
            sig_table.setStyle(TableStyle([
                ('FONTNAME',    (0,0), (-1,-1), 'Helvetica'),
                ('FONTSIZE',    (0,0), (-1,-1), 9),
                ('FONTNAME',    (1,0), (1,0), 'Helvetica-Bold'),
                ('FONTSIZE',    (1,0), (1,0), 14),
                ('TEXTCOLOR',   (1,0), (1,0), sig_col),
                ('FONTNAME',    (0,0), (0,-1), 'Helvetica-Bold'),
                ('FONTNAME',    (2,0), (2,-1), 'Helvetica-Bold'),
                ('TEXTCOLOR',   (0,0), (0,-1), colors.HexColor('#4a5568')),
                ('TEXTCOLOR',   (2,0), (2,-1), colors.HexColor('#4a5568')),
                ('GRID',        (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.HexColor('#f0fdf4'), colors.white]),
                ('PADDING',     (0,0), (-1,-1), 8),
            ]))
            story.append(sig_table)
            story.append(Spacer(1, 0.3*cm))

            # Signal reason
            reason = self.signal.get('reason', 'Multi-indicator confluence detected')
            story.append(Paragraph(f"<b>Analysis Basis:</b> {reason}", body_style))
            story.append(Spacer(1, 0.4*cm))

            # ── Chart Patterns ────────────────────────────────────
            if self.pd_.detected_patterns:
                story.append(Paragraph("DETECTED CHART PATTERNS", h2_style))
                pattern_rows = [['Pattern Name', 'Signal', 'Confidence', 'Description']]
                for p in self.pd_.detected_patterns[:6]:
                    pattern_rows.append([
                        p['name'],
                        p.get('signal', 'N/A').upper(),
                        f"{p.get('confidence', 70):.0f}%",
                        p.get('description', '')[:60]
                    ])
                pat_table = Table(pattern_rows, colWidths=[3.5*cm, 2.5*cm, 2.5*cm, 7.5*cm])
                pat_table.setStyle(TableStyle([
                    ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE',    (0,0), (-1,-1), 9),
                    ('BACKGROUND',  (0,0), (-1,0), colors.HexColor('#f1f5f9')),
                    ('GRID',        (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#fafafa')]),
                    ('PADDING',     (0,0), (-1,-1), 6),
                ]))
                story.append(pat_table)
                story.append(Spacer(1, 0.4*cm))

            # ── Statistics ────────────────────────────────────────
            story.append(Paragraph("QUANTITATIVE STATISTICS", h2_style))
            returns = self.df['close'].pct_change().dropna()
            sharpe  = returns.mean() / returns.std() * (252**0.5) if returns.std() != 0 else 0
            max_dd  = ((self.df['close'] / self.df['close'].cummax()) - 1).min() * 100

            stats_data = [
                ['Win Rate', f"{self.ta.stats.get('win_rate', 55):.1f}%",
                 'Risk/Reward', f"{self.ta.stats.get('risk_reward', 2):.2f}x"],
                ['Volatility (Ann.)', f"{self.ta.stats.get('volatility', 0):.2f}%",
                 'Sharpe Ratio', f"{sharpe:.2f}"],
                ['Max Drawdown', f"{max_dd:.2f}%",
                 'Trend Score', f"{self.ta.stats.get('trend_score', 50):.0f}/100"],
            ]
            stats_table = Table(stats_data, colWidths=[4*cm, 4*cm, 4*cm, 4*cm])
            stats_table.setStyle(TableStyle([
                ('FONTNAME',    (0,0), (-1,-1), 'Helvetica'),
                ('FONTSIZE',    (0,0), (-1,-1), 9),
                ('FONTNAME',    (0,0), (0,-1), 'Helvetica-Bold'),
                ('FONTNAME',    (2,0), (2,-1), 'Helvetica-Bold'),
                ('TEXTCOLOR',   (0,0), (0,-1), colors.HexColor('#4a5568')),
                ('TEXTCOLOR',   (2,0), (2,-1), colors.HexColor('#4a5568')),
                ('GRID',        (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.HexColor('#f8fafc'), colors.white]),
                ('PADDING',     (0,0), (-1,-1), 8),
            ]))
            story.append(stats_table)
            story.append(Spacer(1, 0.4*cm))

            # ── SMC / ICT Summary ─────────────────────────────────
            story.append(Paragraph("TRADING SCHOOLS ANALYSIS", h2_style))

            smc = self.schools.smc_analysis
            ict = self.schools.ict_analysis
            sk  = self.schools.sk_analysis

            schools_data = [
                ['School', 'Bias', 'Key Signal', 'Status'],
                ['Smart Money (SMC)', smc.get('trend','N/A'),
                 smc.get('bias','N/A')[:40], 'Active'],
                ['ICT Concepts', ict.get('daily_bias','N/A')[:20],
                 ict.get('power_of_3','N/A')[:40], 'Active'],
                ['SK System', sk.get('signal','N/A'),
                 sk.get('phase','N/A')[:40], 'Active'],
            ]
            schools_table = Table(schools_data, colWidths=[3.5*cm, 3*cm, 8*cm, 1.5*cm])
            schools_table.setStyle(TableStyle([
                ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE',    (0,0), (-1,-1), 9),
                ('BACKGROUND',  (0,0), (-1,0), colors.HexColor('#f1f5f9')),
                ('GRID',        (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#fafafa')]),
                ('PADDING',     (0,0), (-1,-1), 6),
            ]))
            story.append(schools_table)
            story.append(Spacer(1, 0.5*cm))

            # ── Disclaimer ────────────────────────────────────────
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e2e8f0')))
            disclaimer_style = ParagraphStyle(
                'Disclaimer', parent=styles['Normal'],
                fontSize=7, textColor=colors.HexColor('#9ca3af'),
                alignment=TA_CENTER, spaceBefore=8
            )
            story.append(Paragraph(
                "⚠️ DISCLAIMER: This report is for educational purposes only and does not constitute financial advice. "
                "Trading involves substantial risk of loss. Past performance does not guarantee future results. "
                "Always use proper risk management. NEXUS Trading Intelligence © 2024",
                disclaimer_style
            ))

            # ── Build PDF ─────────────────────────────────────────
            doc.build(story)
            return filepath

        except Exception as e:
            print(f"PDF generation error: {e}")
            return None
