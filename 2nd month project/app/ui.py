"""
Centralized UI system and reusable visual primitives for SmartHire GenAI.
Supports enterprise-grade Light Mode and Dark Mode with dynamic token injection,
specular button reflections, and responsive workflow primitives.
"""

from typing import List, Dict, Any, Optional
import html
import streamlit as st


def inject_global_styles(theme_mode: str = "light"):
    """
    Injects core design tokens and application styling into the Streamlit page.
    Supports both 'light' and 'dark' modes dynamically.
    """
    is_dark = str(theme_mode).strip().lower() == "dark"

    if is_dark:
        # DARK MODE DESIGN TOKENS (Deep obsidian / slate SaaS palette)
        token_vars = """
        --sh-bg: #0b0f19;
        --sh-surface: #131b2e;
        --sh-surface-subtle: #1a243b;
        --sh-surface-muted: #24304d;
        --sh-surface-hover: #263554;
        --sh-border: #24304d;
        --sh-border-subtle: #1a243b;
        --sh-border-strong: #3b4d75;
        --sh-text: #f8fafc;
        --sh-text-muted: #94a3b8;
        --sh-text-subtle: #64748b;
        --sh-primary: #3b82f6;
        --sh-primary-hover: #60a5fa;
        --sh-primary-subtle: rgba(59, 130, 246, 0.16);
        --sh-primary-border: rgba(59, 130, 246, 0.35);
        --sh-success: #34d399;
        --sh-success-subtle: rgba(52, 211, 153, 0.14);
        --sh-success-border: rgba(52, 211, 153, 0.32);
        --sh-warning: #fbbf24;
        --sh-warning-subtle: rgba(251, 191, 36, 0.14);
        --sh-warning-border: rgba(251, 191, 36, 0.32);
        --sh-danger: #f87171;
        --sh-danger-subtle: rgba(248, 113, 113, 0.14);
        --sh-danger-border: rgba(248, 113, 113, 0.32);
        --sh-radius-sm: 6px;
        --sh-radius: 8px;
        --sh-radius-lg: 12px;
        --sh-shadow-xs: 0 1px 3px 0 rgba(0, 0, 0, 0.4);
        --sh-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.45), 0 2px 4px -2px rgba(0, 0, 0, 0.3);
        --sh-shadow-md: 0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -4px rgba(0, 0, 0, 0.35);
        --sh-font-sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;

        /* Component-specific tokens */
        --sh-sidebar-bg: #080c14;
        --sh-sidebar-border: #1e293b;
        --sh-sidebar-btn-color: #cbd5e1;
        --sh-sidebar-btn-hover-bg: #1e293b;
        --sh-sidebar-btn-hover-color: #f8fafc;
        --sh-sidebar-btn-hover-border: #334155;

        --sh-input-bg: #131b2e;
        --sh-input-color: #f8fafc;
        --sh-input-border: #24304d;

        --sh-btn-sec-bg: #131b2e;
        --sh-btn-sec-color: #e2e8f0;
        --sh-btn-sec-border: #2e3d61;
        --sh-btn-sec-hover-bg: #1e293b;
        --sh-btn-sec-hover-color: #ffffff;
        --sh-btn-sec-hover-border: #475569;

        --sh-chip-bg: #1a243b;
        --sh-chip-color: #cbd5e1;
        --sh-chip-border: #24304d;
        --sh-card-bg: #131b2e;
        """
    else:
        # LIGHT MODE DESIGN TOKENS (Crisp enterprise SaaS palette)
        token_vars = """
        --sh-bg: #ffffff;
        --sh-surface: #ffffff;
        --sh-surface-subtle: #f8fafc;
        --sh-surface-muted: #f1f5f9;
        --sh-surface-hover: #f1f5f9;
        --sh-border: #e2e8f0;
        --sh-border-subtle: #edf2f7;
        --sh-border-strong: #cbd5e1;
        --sh-text: #0f172a;
        --sh-text-muted: #64748b;
        --sh-text-subtle: #94a3b8;
        --sh-primary: #1d4ed8;
        --sh-primary-hover: #1e40af;
        --sh-primary-subtle: #eff6ff;
        --sh-primary-border: #bfdbfe;
        --sh-success: #15803d;
        --sh-success-subtle: #f0fdf4;
        --sh-success-border: #bbf7d0;
        --sh-warning: #b45309;
        --sh-warning-subtle: #fffbeb;
        --sh-warning-border: #fde68a;
        --sh-danger: #b91c1c;
        --sh-danger-subtle: #fef2f2;
        --sh-danger-border: #fecaca;
        --sh-radius-sm: 6px;
        --sh-radius: 8px;
        --sh-radius-lg: 12px;
        --sh-shadow-xs: 0 1px 2px 0 rgba(15, 23, 42, 0.04);
        --sh-shadow: 0 1px 3px 0 rgba(15, 23, 42, 0.06), 0 1px 2px -1px rgba(15, 23, 42, 0.04);
        --sh-shadow-md: 0 4px 6px -1px rgba(15, 23, 42, 0.07), 0 2px 4px -2px rgba(15, 23, 42, 0.04);
        --sh-font-sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;

        /* Component-specific tokens */
        --sh-sidebar-bg: #f8fafc;
        --sh-sidebar-border: #e2e8f0;
        --sh-sidebar-btn-color: #334155;
        --sh-sidebar-btn-hover-bg: #f1f5f9;
        --sh-sidebar-btn-hover-color: #0f172a;
        --sh-sidebar-btn-hover-border: #e2e8f0;

        --sh-input-bg: #ffffff;
        --sh-input-color: #0f172a;
        --sh-input-border: #e2e8f0;

        --sh-btn-sec-bg: #ffffff;
        --sh-btn-sec-color: #334155;
        --sh-btn-sec-border: #cbd5e1;
        --sh-btn-sec-hover-bg: #f8fafc;
        --sh-btn-sec-hover-color: #0f172a;
        --sh-btn-sec-hover-border: #94a3b8;

        --sh-chip-bg: #f1f5f9;
        --sh-chip-color: #334155;
        --sh-chip-border: #e2e8f0;
        --sh-card-bg: #ffffff;
        """

    css = f"""
    <style>
    /* =========================================================
       SMARTHIRE DESIGN SYSTEM TOKENS (Mode: {'Dark' if is_dark else 'Light'})
       ========================================================= */
    :root {{
        {token_vars}
    }}

    /* =========================================================
       APP SHELL & RESPONSIVE LAYOUT CONSTRAINTS
       ========================================================= */
    .stApp {{
        background-color: var(--sh-bg) !important;
        color: var(--sh-text) !important;
        font-family: var(--sh-font-sans);
    }}

    /* Streamlit top header bar */
    header[data-testid="stHeader"],
    [data-testid="stHeader"] {{
        background-color: var(--sh-bg) !important;
        border-bottom: 1px solid var(--sh-border-subtle) !important;
    }}

    header[data-testid="stHeader"] *,
    [data-testid="stHeader"] * {{
        color: var(--sh-text) !important;
    }}

    /* Controlled central content area - prevent ultra-wide distortion & header overlap */
    .stMain .block-container,
    [data-testid="stMain"] .block-container,
    .stMainBlockContainer {{
        max-width: 1060px !important;
        padding-top: 3.75rem !important;
        padding-bottom: 3.5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }}

    /* Sidebar styling */
    [data-testid="stSidebar"] {{
        background-color: var(--sh-sidebar-bg) !important;
        border-right: 1px solid var(--sh-sidebar-border) !important;
    }}

    [data-testid="stSidebar"] .block-container {{
        padding-top: 1.75rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }}

    /* Sidebar Navigation Button Styling */
    [data-testid="stSidebar"] .stButton > button {{
        display: flex !important;
        justify-content: flex-start !important;
        align-items: center !important;
        text-align: left !important;
        width: 100% !important;
        padding: 0.5rem 0.85rem !important;
        border-radius: var(--sh-radius-sm) !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        margin-bottom: 0.25rem !important;
        border: 1px solid transparent !important;
        transition: all 0.15s ease !important;
    }}

    [data-testid="stSidebar"] .stButton > button[kind="secondary"] {{
        background-color: transparent !important;
        color: var(--sh-sidebar-btn-color) !important;
        border-color: transparent !important;
    }}

    [data-testid="stSidebar"] .stButton > button[kind="secondary"] * {{
        color: var(--sh-sidebar-btn-color) !important;
    }}

    [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {{
        background-color: var(--sh-sidebar-btn-hover-bg) !important;
        color: var(--sh-sidebar-btn-hover-color) !important;
        border-color: var(--sh-sidebar-btn-hover-border) !important;
    }}

    [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover * {{
        color: var(--sh-sidebar-btn-hover-color) !important;
    }}

    [data-testid="stSidebar"] .stButton > button[kind="primary"] {{
        background-color: var(--sh-primary) !important;
        color: #ffffff !important;
        border-color: var(--sh-primary) !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.2) !important;
    }}

    [data-testid="stSidebar"] .stButton > button[kind="primary"] * {{
        color: #ffffff !important;
    }}

    /* Headings and Typography */
    h1, h2, h3, h4, h5, h6 {{
        color: var(--sh-text) !important;
        font-family: var(--sh-font-sans) !important;
        font-weight: 600 !important;
        letter-spacing: -0.015em;
    }}

    /* Standalone markdown text - NEVER override button or segmented control text */
    .stMarkdown:not(button *):not([data-testid="stSegmentedControl"] *) p,
    div.stMarkdownContainer > p {{
        color: var(--sh-text);
    }}

    /* Button and interactive controls text MUST inherit explicit element colors */
    button p,
    button [data-testid="stMarkdownContainer"] p,
    button [data-testid="stMarkdownContainer"] span,
    button span {{
        color: inherit !important;
    }}

    div[data-testid="stSegmentedControl"] button p,
    div[data-testid="stSegmentedControl"] button [data-testid="stMarkdownContainer"] p,
    div[data-testid="stSegmentedControl"] button span {{
        color: inherit !important;
    }}

    /* =========================================================
       STREAMLIT COMPONENT REFINEMENTS
       ========================================================= */
    /* Container cards */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        border-color: var(--sh-border) !important;
        border-radius: var(--sh-radius) !important;
        background-color: var(--sh-surface) !important;
        box-shadow: var(--sh-shadow-xs) !important;
    }}

    /* Expander styling */
    [data-testid="stExpander"] {{
        border-radius: var(--sh-radius) !important;
        border-color: var(--sh-border) !important;
        background-color: var(--sh-surface) !important;
        box-shadow: none !important;
        margin-bottom: 0.75rem !important;
    }}

    [data-testid="stExpander"] summary {{
        color: var(--sh-text) !important;
    }}

    [data-testid="stExpander"] summary * {{
        color: var(--sh-text) !important;
    }}

    [data-testid="stExpander"] summary:hover {{
        color: var(--sh-primary) !important;
    }}

    [data-testid="stExpander"] summary:hover * {{
        color: var(--sh-primary) !important;
    }}

    [data-testid="stExpander"] details {{
        color: var(--sh-text) !important;
    }}

    /* =========================================================
       CHATGPT-INSPIRED CHAT MESSAGE SYSTEM & ANIMATIONS
       ========================================================= */
    @keyframes chatFadeIn {{
        from {{
            opacity: 0;
            transform: translateY(8px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}

    @keyframes pulseGlow {{
        0%, 100% {{ opacity: 0.4; }}
        50% {{ opacity: 1; }}
    }}

    /* Base Chat Message Container */
    [data-testid="stChatMessage"] {{
        animation: chatFadeIn 0.28s cubic-bezier(0.16, 1, 0.3, 1) forwards !important;
        padding: 0.75rem 1rem !important;
        margin-bottom: 0.85rem !important;
        border-radius: 14px !important;
        border: none !important;
        background-color: transparent !important;
        box-shadow: none !important;
        color: var(--sh-text) !important;
    }}

    [data-testid="stChatMessage"] p {{
        color: var(--sh-text) !important;
        font-size: 0.95rem !important;
        line-height: 1.6 !important;
    }}

    /* User Message Bubble: Distinct ChatGPT-style right-aligned / pill bubble */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {{
        background-color: var(--sh-surface-hover) !important;
        border: 1px solid var(--sh-border-subtle) !important;
        border-radius: 18px 18px 4px 18px !important;
        padding: 0.75rem 1.15rem !important;
        max-width: 86% !important;
        margin-left: auto !important;
        margin-right: 0 !important;
    }}

    /* Assistant Message Container: Seamless open canvas like ChatGPT */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {{
        background-color: transparent !important;
        border: none !important;
        padding: 0.5rem 0.5rem 0.5rem 0 !important;
        max-width: 100% !important;
    }}

    /* Avatar Icons - Modern rounded styling */
    [data-testid="stChatMessageAvatar"],
    div[data-testid="stChatMessageAvatar"] {{
        background-color: var(--sh-surface-muted) !important;
        border: 1px solid var(--sh-border) !important;
        border-radius: 50% !important;
        width: 32px !important;
        height: 32px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}

    [data-testid="stChatMessageAvatar"] svg,
    div[data-testid="stChatMessageAvatar"] svg {{
        width: 18px !important;
        height: 18px !important;
        color: var(--sh-primary) !important;
    }}

    /* =========================================================
       SPECULAR BUTTON SYSTEM (PRIMARY HERO ACTIONS)
       Reference: SpecularButton (baseColor: #525252, radius: 18px,
       textColor: #f5f5f5, specular shine, inner highlight, lift)
       ========================================================= */
    .stMain div.stButton button[kind="primary"],
    .stMain div[data-testid="stButton"] button[kind="primary"],
    .stMain div.stFormSubmitButton button[kind="primary"],
    .stMain div[data-testid="stFormSubmitButton"] button[kind="primary"],
    [data-testid="stMain"] div.stButton button[kind="primary"],
    [data-testid="stMain"] div[data-testid="stButton"] button[kind="primary"],
    [data-testid="stMain"] div.stFormSubmitButton button[kind="primary"],
    [data-testid="stMain"] div[data-testid="stFormSubmitButton"] button[kind="primary"] {{
        position: relative !important;
        overflow: hidden !important;
        min-height: 46px !important;
        padding: 0.55rem 1.6rem !important;
        border-radius: 18px !important;
        color: #f5f5f5 !important;
        background:
            linear-gradient(
                135deg,
                rgba(255, 255, 255, 0.14) 0%,
                rgba(255, 255, 255, 0.04) 35%,
                rgba(0, 0, 0, 0.12) 100%
            ),
            #525252 !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em !important;
        box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.20),
            inset 0 -1px 0 rgba(0, 0, 0, 0.25),
            0 8px 24px rgba(0, 0, 0, 0.24) !important;
        transition:
            transform 0.22s ease,
            box-shadow 0.22s ease,
            border-color 0.22s ease,
            background 0.22s ease !important;
        z-index: 1 !important;
    }}

    .stMain div.stButton button[kind="primary"] *,
    .stMain div[data-testid="stButton"] button[kind="primary"] *,
    .stMain div.stFormSubmitButton button[kind="primary"] *,
    .stMain div[data-testid="stFormSubmitButton"] button[kind="primary"] *,
    [data-testid="stMain"] div.stButton button[kind="primary"] *,
    [data-testid="stMain"] div[data-testid="stButton"] button[kind="primary"] *,
    [data-testid="stMain"] div.stFormSubmitButton button[kind="primary"] *,
    [data-testid="stMain"] div[data-testid="stFormSubmitButton"] button[kind="primary"] * {{
        color: #f5f5f5 !important;
        font-size: 15px !important;
        font-weight: 600 !important;
    }}

    /* Specular Diagonal Reflection Sweep */
    .stMain div.stButton button[kind="primary"]::before,
    .stMain div[data-testid="stButton"] button[kind="primary"]::before,
    .stMain div.stFormSubmitButton button[kind="primary"]::before,
    .stMain div[data-testid="stFormSubmitButton"] button[kind="primary"]::before,
    [data-testid="stMain"] div.stButton button[kind="primary"]::before,
    [data-testid="stMain"] div[data-testid="stButton"] button[kind="primary"]::before,
    [data-testid="stMain"] div.stFormSubmitButton button[kind="primary"]::before,
    [data-testid="stMain"] div[data-testid="stFormSubmitButton"] button[kind="primary"]::before {{
        content: "" !important;
        position: absolute !important;
        top: -90% !important;
        left: -50% !important;
        width: 45% !important;
        height: 280% !important;
        transform: rotate(20deg) !important;
        background: linear-gradient(
            90deg,
            transparent,
            rgba(255, 255, 255, 0.45),
            transparent
        ) !important;
        filter: blur(8px) !important;
        opacity: 0 !important;
        pointer-events: none !important;
        transition:
            left 0.55s ease,
            opacity 0.25s ease !important;
        z-index: 2 !important;
    }}

    /* Specular Button Hover: Lift, border illumination, and shine streak */
    .stMain div.stButton button[kind="primary"]:hover,
    .stMain div[data-testid="stButton"] button[kind="primary"]:hover,
    .stMain div.stFormSubmitButton button[kind="primary"]:hover,
    .stMain div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover,
    [data-testid="stMain"] div.stButton button[kind="primary"]:hover,
    [data-testid="stMain"] div[data-testid="stButton"] button[kind="primary"]:hover,
    [data-testid="stMain"] div.stFormSubmitButton button[kind="primary"]:hover,
    [data-testid="stMain"] div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {{
        transform: translateY(-2px) !important;
        border-color: rgba(255, 255, 255, 0.40) !important;
        box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.30),
            inset 0 -1px 0 rgba(0, 0, 0, 0.25),
            0 12px 32px rgba(0, 0, 0, 0.35) !important;
    }}

    .stMain div.stButton button[kind="primary"]:hover::before,
    .stMain div[data-testid="stButton"] button[kind="primary"]:hover::before,
    .stMain div.stFormSubmitButton button[kind="primary"]:hover::before,
    .stMain div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover::before,
    [data-testid="stMain"] div.stButton button[kind="primary"]:hover::before,
    [data-testid="stMain"] div[data-testid="stButton"] button[kind="primary"]:hover::before,
    [data-testid="stMain"] div.stFormSubmitButton button[kind="primary"]:hover::before,
    [data-testid="stMain"] div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover::before {{
        left: 135% !important;
        opacity: 1 !important;
    }}

    /* Specular Button Active / Clicked */
    .stMain div.stButton button[kind="primary"]:active,
    .stMain div[data-testid="stButton"] button[kind="primary"]:active,
    .stMain div.stFormSubmitButton button[kind="primary"]:active,
    .stMain div[data-testid="stFormSubmitButton"] button[kind="primary"]:active,
    [data-testid="stMain"] div.stButton button[kind="primary"]:active,
    [data-testid="stMain"] div[data-testid="stButton"] button[kind="primary"]:active,
    [data-testid="stMain"] div.stFormSubmitButton button[kind="primary"]:active,
    [data-testid="stMain"] div[data-testid="stFormSubmitButton"] button[kind="primary"]:active {{
        transform: translateY(0) scale(0.99) !important;
        box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.10),
            inset 0 2px 4px rgba(0, 0, 0, 0.25),
            0 4px 14px rgba(0, 0, 0, 0.18) !important;
    }}

    /* Specular Button Accessible Keyboard Focus */
    .stMain div.stButton button[kind="primary"]:focus-visible,
    .stMain div[data-testid="stButton"] button[kind="primary"]:focus-visible,
    .stMain div.stFormSubmitButton button[kind="primary"]:focus-visible,
    .stMain div[data-testid="stFormSubmitButton"] button[kind="primary"]:focus-visible,
    [data-testid="stMain"] div.stButton button[kind="primary"]:focus-visible,
    [data-testid="stMain"] div[data-testid="stButton"] button[kind="primary"]:focus-visible,
    [data-testid="stMain"] div.stFormSubmitButton button[kind="primary"]:focus-visible,
    [data-testid="stMain"] div[data-testid="stFormSubmitButton"] button[kind="primary"]:focus-visible {{
        outline: 2px solid rgba(255, 255, 255, 0.80) !important;
        outline-offset: 3px !important;
    }}

    /* =========================================================
       SECONDARY BUTTON SYSTEM (OUTLINED & THEME-AWARE)
       ========================================================= */
    .stMain div.stButton button[kind="secondary"],
    .stMain div[data-testid="stButton"] button[kind="secondary"],
    .stMain div.stFormSubmitButton button[kind="secondary"],
    .stMain div[data-testid="stFormSubmitButton"] button[kind="secondary"],
    [data-testid="stMain"] div.stButton button[kind="secondary"],
    [data-testid="stMain"] div[data-testid="stButton"] button[kind="secondary"],
    [data-testid="stMain"] div.stFormSubmitButton button[kind="secondary"],
    [data-testid="stMain"] div[data-testid="stFormSubmitButton"] button[kind="secondary"] {{
        position: relative !important;
        min-height: 40px !important;
        padding: 0.45rem 1.25rem !important;
        border-radius: 12px !important;
        background-color: var(--sh-btn-sec-bg) !important;
        color: var(--sh-btn-sec-color) !important;
        border: 1px solid var(--sh-btn-sec-border) !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        box-shadow: var(--sh-shadow-xs) !important;
        transition:
            transform 0.18s ease,
            border-color 0.18s ease,
            background-color 0.18s ease,
            color 0.18s ease,
            box-shadow 0.18s ease !important;
    }}

    .stMain div.stButton button[kind="secondary"] *,
    .stMain div[data-testid="stButton"] button[kind="secondary"] *,
    .stMain div.stFormSubmitButton button[kind="secondary"] *,
    .stMain div[data-testid="stFormSubmitButton"] button[kind="secondary"] *,
    [data-testid="stMain"] div.stButton button[kind="secondary"] *,
    [data-testid="stMain"] div[data-testid="stButton"] button[kind="secondary"] *,
    [data-testid="stMain"] div.stFormSubmitButton button[kind="secondary"] *,
    [data-testid="stMain"] div[data-testid="stFormSubmitButton"] button[kind="secondary"] * {{
        color: var(--sh-btn-sec-color) !important;
        font-weight: 500 !important;
    }}

    .stMain div.stButton button[kind="secondary"]:hover,
    .stMain div[data-testid="stButton"] button[kind="secondary"]:hover,
    .stMain div.stFormSubmitButton button[kind="secondary"]:hover,
    .stMain div[data-testid="stFormSubmitButton"] button[kind="secondary"]:hover,
    [data-testid="stMain"] div.stButton button[kind="secondary"]:hover,
    [data-testid="stMain"] div[data-testid="stButton"] button[kind="secondary"]:hover,
    [data-testid="stMain"] div.stFormSubmitButton button[kind="secondary"]:hover,
    [data-testid="stMain"] div[data-testid="stFormSubmitButton"] button[kind="secondary"]:hover {{
        background-color: var(--sh-btn-sec-hover-bg) !important;
        border-color: var(--sh-btn-sec-hover-border) !important;
        color: var(--sh-btn-sec-hover-color) !important;
        transform: translateY(-1px) !important;
        box-shadow: var(--sh-shadow) !important;
    }}

    .stMain div.stButton button[kind="secondary"]:hover *,
    .stMain div[data-testid="stButton"] button[kind="secondary"]:hover *,
    .stMain div.stFormSubmitButton button[kind="secondary"]:hover *,
    .stMain div[data-testid="stFormSubmitButton"] button[kind="secondary"]:hover *,
    [data-testid="stMain"] div.stButton button[kind="secondary"]:hover *,
    [data-testid="stMain"] div[data-testid="stButton"] button[kind="secondary"]:hover *,
    [data-testid="stMain"] div.stFormSubmitButton button[kind="secondary"]:hover *,
    [data-testid="stMain"] div[data-testid="stFormSubmitButton"] button[kind="secondary"]:hover * {{
        color: var(--sh-btn-sec-hover-color) !important;
    }}

    .stMain div.stButton button[kind="secondary"]:active,
    .stMain div[data-testid="stButton"] button[kind="secondary"]:active,
    .stMain div.stFormSubmitButton button[kind="secondary"]:active,
    .stMain div[data-testid="stFormSubmitButton"] button[kind="secondary"]:active,
    [data-testid="stMain"] div.stButton button[kind="secondary"]:active,
    [data-testid="stMain"] div[data-testid="stButton"] button[kind="secondary"]:active,
    [data-testid="stMain"] div.stFormSubmitButton button[kind="secondary"]:active,
    [data-testid="stMain"] div[data-testid="stFormSubmitButton"] button[kind="secondary"]:active {{
        transform: translateY(0) !important;
    }}

    .stMain div.stButton button[kind="secondary"]:focus-visible,
    .stMain div[data-testid="stButton"] button[kind="secondary"]:focus-visible,
    .stMain div.stFormSubmitButton button[kind="secondary"]:focus-visible,
    .stMain div[data-testid="stFormSubmitButton"] button[kind="secondary"]:focus-visible,
    [data-testid="stMain"] div.stButton button[kind="secondary"]:focus-visible,
    [data-testid="stMain"] div[data-testid="stButton"] button[kind="secondary"]:focus-visible,
    [data-testid="stMain"] div.stFormSubmitButton button[kind="secondary"]:focus-visible,
    [data-testid="stMain"] div[data-testid="stFormSubmitButton"] button[kind="secondary"]:focus-visible {{
        outline: 2px solid var(--sh-primary) !important;
        outline-offset: 2px !important;
    }}

    /* Compact utility buttons (Feedback buttons) */
    .stMain div.stButton button[key*="rel_"],
    .stMain div.stButton button[key*="irrel_"],
    .stMain div.stButton button[key*="f_help_"],
    .stMain div.stButton button[key*="f_unhelp_"],
    [data-testid="stMain"] div.stButton button[key*="rel_"],
    [data-testid="stMain"] div.stButton button[key*="irrel_"],
    [data-testid="stMain"] div.stButton button[key*="f_help_"],
    [data-testid="stMain"] div.stButton button[key*="f_unhelp_"] {{
        min-height: 32px !important;
        padding: 0.25rem 0.8rem !important;
        border-radius: 8px !important;
        font-size: 0.82rem !important;
    }}

    /* Destructive hover on replace/reject buttons */
    .stMain div.stButton button[key*="replace"]:hover,
    .stMain div.stButton button[key*="reject"]:hover,
    [data-testid="stMain"] div.stButton button[key*="replace"]:hover,
    [data-testid="stMain"] div.stButton button[key*="reject"]:hover {{
        border-color: var(--sh-danger-border) !important;
        color: var(--sh-danger) !important;
        background-color: var(--sh-danger-subtle) !important;
    }}

    .stMain div.stButton button[key*="replace"]:hover *,
    .stMain div.stButton button[key*="reject"]:hover *,
    [data-testid="stMain"] div.stButton button[key*="replace"]:hover *,
    [data-testid="stMain"] div.stButton button[key*="reject"]:hover * {{
        color: var(--sh-danger) !important;
    }}

    /* Bottom fixed area and chat input container */
    [data-testid="stBottom"],
    .stBottom,
    .stBottom > div,
    [data-testid="stBottom"] > div {{
        background-color: var(--sh-bg) !important;
        border-top: 1px solid var(--sh-border-subtle) !important;
    }}

    [data-testid="stChatInput"] {{
        background-color: var(--sh-surface) !important;
        border: 1.5px solid var(--sh-border) !important;
        border-radius: 16px !important;
        box-shadow: var(--sh-shadow) !important;
        padding: 4px 8px !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }}

    [data-testid="stChatInput"]:focus-within {{
        border-color: var(--sh-primary) !important;
        box-shadow: 0 0 0 3px var(--sh-primary-subtle), var(--sh-shadow-md) !important;
    }}

    /* REMOVE NESTED BOX ARTIFACTS: Strip background, borders, and outlines from all inner wrappers and textarea */
    [data-testid="stChatInput"] *,
    [data-testid="stChatInput"] > div,
    [data-testid="stChatInput"] div[data-baseweb="base-input"],
    [data-testid="stChatInput"] div[data-baseweb="input"],
    [data-testid="stChatInput"] [class*="st-emotion-cache"] {{
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}

    [data-testid="stChatInput"] textarea,
    [data-testid="stChatInputTextArea"] {{
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
        color: var(--sh-text) !important;
        font-family: var(--sh-font-sans) !important;
        font-size: 0.95rem !important;
        line-height: 1.5 !important;
        resize: none !important;
        padding: 8px 10px !important;
    }}

    [data-testid="stChatInput"] textarea::placeholder {{
        color: var(--sh-text-muted) !important;
        opacity: 0.75 !important;
    }}

    /* Send / Submit button inside chat input */
    [data-testid="stChatInputSubmitButton"],
    button[data-testid="stChatInputSubmitButton"] {{
        background-color: var(--sh-primary) !important;
        color: #ffffff !important;
        border-radius: 10px !important;
        border: none !important;
        width: 36px !important;
        height: 36px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: transform 0.15s ease, background-color 0.15s ease !important;
    }}

    [data-testid="stChatInputSubmitButton"]:hover {{
        background-color: var(--sh-primary-hover) !important;
        transform: scale(1.05) !important;
    }}

    [data-testid="stChatInputSubmitButton"] svg {{
        fill: #ffffff !important;
        color: #ffffff !important;
    }}

    [data-testid="stChatInputSubmitButton"]:disabled,
    [data-testid="stChatInputSubmitButton"][disabled] {{
        background-color: var(--sh-surface-muted) !important;
        opacity: 0.4 !important;
        cursor: not-allowed !important;
    }}

    /* Attachment (+) button inside chat input */
    [data-testid="stChatInputFileUploadButton"],
    button[data-testid="stChatInputFileUploadButton"] {{
        background: transparent !important;
        border: none !important;
        color: var(--sh-text-muted) !important;
        border-radius: 8px !important;
        transition: color 0.15s ease, background-color 0.15s ease !important;
    }}

    [data-testid="stChatInputFileUploadButton"]:hover {{
        color: var(--sh-primary) !important;
        background-color: var(--sh-surface-hover) !important;
    }}

    /* =========================================================
       POPOVER TRIGGER BUTTONS (History, Memory toolbar)
       ========================================================= */
    .stPopover > button,
    [data-testid="stPopoverButton"],
    div[data-testid="stPopover"] > button {{
        background-color: var(--sh-btn-sec-bg) !important;
        color: var(--sh-btn-sec-color) !important;
        border: 1px solid var(--sh-btn-sec-border) !important;
        border-radius: var(--sh-radius) !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        padding: 0.45rem 1rem !important;
        min-height: 38px !important;
        transition: all 0.18s ease !important;
        width: 100% !important;
    }}

    .stPopover > button *,
    [data-testid="stPopoverButton"] *,
    div[data-testid="stPopover"] > button * {{
        color: var(--sh-btn-sec-color) !important;
    }}

    .stPopover > button:hover,
    [data-testid="stPopoverButton"]:hover,
    div[data-testid="stPopover"] > button:hover {{
        background-color: var(--sh-btn-sec-hover-bg) !important;
        border-color: var(--sh-btn-sec-hover-border) !important;
        color: var(--sh-btn-sec-hover-color) !important;
        transform: translateY(-1px) !important;
        box-shadow: var(--sh-shadow) !important;
    }}

    .stPopover > button:hover *,
    [data-testid="stPopoverButton"]:hover *,
    div[data-testid="stPopover"] > button:hover * {{
        color: var(--sh-btn-sec-hover-color) !important;
    }}

    /* Popover dropdown panel */
    .stPopover [data-testid="stPopoverBody"],
    div[data-baseweb="popover"] > div {{
        width: 395px !important;
        max-width: min(415px, calc(100vw - 28px)) !important;
        max-height: 74vh !important;
        background-color: var(--sh-surface) !important;
        border: 1px solid var(--sh-border) !important;
        border-radius: 18px !important;
        box-shadow: 0 16px 36px -4px rgba(0, 0, 0, 0.55), 0 0 0 1px var(--sh-border-subtle) !important;
        backdrop-filter: blur(18px) !important;
        -webkit-backdrop-filter: blur(18px) !important;
        padding: 16px 18px 14px 18px !important;
        overflow-x: hidden !important;
    }}

    .stPopover [data-testid="stPopoverBody"] *,
    .stPopover [data-testid="stPopoverBody"] p,
    .stPopover [data-testid="stPopoverBody"] span,
    .stPopover [data-testid="stPopoverBody"] label {{
        color: var(--sh-text) !important;
    }}

    /* =========================================================
       CHAT MESSAGES (ChatGPT-style bubbles)
       ========================================================= */
    [data-testid="stChatMessage"] {{
        background-color: transparent !important;
        border: none !important;
        padding: 0.75rem 0 !important;
        margin: 0 !important;
    }}

    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p {{
        color: var(--sh-text) !important;
        font-size: 0.95rem !important;
        line-height: 1.65 !important;
    }}

    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h1,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h2,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h3,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h4 {{
        color: var(--sh-text) !important;
        font-weight: 600 !important;
        margin-top: 0.8rem !important;
    }}

    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] strong {{
        color: var(--sh-text) !important;
        font-weight: 600 !important;
    }}

    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {{
        color: var(--sh-text) !important;
        margin-bottom: 0.25rem !important;
    }}

    /* Chat message avatar */
    [data-testid="stChatMessage"] [data-testid="stChatMessageAvatarCustom"],
    [data-testid="stChatMessage"] .stChatMessageAvatar {{
        border-radius: 50% !important;
    }}

    /* Expander inside chat messages (Sources, Thought process) */
    [data-testid="stChatMessage"] [data-testid="stExpander"] {{
        border: 1px solid var(--sh-border-subtle) !important;
        border-radius: var(--sh-radius) !important;
        background-color: var(--sh-surface-subtle) !important;
    }}

    [data-testid="stChatMessage"] [data-testid="stExpander"] summary {{
        color: var(--sh-text-muted) !important;
        font-size: 0.85rem !important;
    }}

    /* Compact status shimmer (Synthesizing...) */
    [data-testid="stStatusWidget"] {{
        background-color: var(--sh-surface-subtle) !important;
        border: 1px solid var(--sh-border-subtle) !important;
        border-radius: var(--sh-radius) !important;
    }}

    /* =========================================================
       ANIMATED TYPING DOTS (ChatGPT-style loading)
       ========================================================= */
    @keyframes sh-typing-dot {{
        0%, 60%, 100% {{ opacity: 0.3; transform: translateY(0); }}
        30% {{ opacity: 1; transform: translateY(-4px); }}
    }}

    .sh-typing-dots {{
        display: inline-flex;
        gap: 4px;
        align-items: center;
        padding: 8px 0;
    }}

    .sh-typing-dots span {{
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: var(--sh-text-muted);
        animation: sh-typing-dot 1.2s ease-in-out infinite;
    }}

    .sh-typing-dots span:nth-child(2) {{ animation-delay: 0.15s; }}
    .sh-typing-dots span:nth-child(3) {{ animation-delay: 0.3s; }}

    /* Tooltips */
    div[data-baseweb="tooltip"],
    div[data-testid="stTooltipContent"] {{
        background-color: var(--sh-surface-muted) !important;
        color: var(--sh-text) !important;
        border: 1px solid var(--sh-border) !important;
        border-radius: var(--sh-radius-sm) !important;
    }}

    /* Inputs, Selectboxes, Textareas, Sliders */
    .stTextInput input, .stTextArea textarea, .stNumberInput input {{
        border-radius: var(--sh-radius-sm) !important;
        border: 1px solid var(--sh-input-border) !important;
        background-color: var(--sh-input-bg) !important;
        color: var(--sh-input-color) !important;
        font-size: 0.875rem !important;
    }}

    .stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {{
        border-color: var(--sh-primary) !important;
        box-shadow: 0 0 0 1px var(--sh-primary) !important;
    }}

    .stSelectbox div[data-baseweb="select"] > div {{
        border-radius: var(--sh-radius-sm) !important;
        border-color: var(--sh-input-border) !important;
        background-color: var(--sh-input-bg) !important;
        color: var(--sh-input-color) !important;
        font-size: 0.875rem !important;
    }}

    .stSelectbox div[data-baseweb="select"] * {{
        color: var(--sh-input-color) !important;
    }}

    /* Dropdown popup menu */
    div[data-baseweb="popover"] ul[role="listbox"] {{
        background-color: var(--sh-surface) !important;
        border: 1px solid var(--sh-border) !important;
        box-shadow: var(--sh-shadow-md) !important;
    }}

    div[data-baseweb="popover"] li[role="option"] {{
        background-color: var(--sh-surface) !important;
        color: var(--sh-text) !important;
    }}

    div[data-baseweb="popover"] li[role="option"]:hover,
    div[data-baseweb="popover"] li[aria-selected="true"] {{
        background-color: var(--sh-surface-hover) !important;
        color: var(--sh-primary) !important;
    }}

    /* Segmented controls / Pills */
    div[data-testid="stSegmentedControl"] {{
        background-color: var(--sh-surface-muted) !important;
        border: 1px solid var(--sh-border) !important;
        border-radius: var(--sh-radius) !important;
        padding: 3px !important;
    }}

    div[data-testid="stSegmentedControl"] button {{
        border-radius: var(--sh-radius-sm) !important;
        background-color: transparent !important;
        color: var(--sh-text-muted) !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        border: none !important;
        transition: all 0.15s ease !important;
    }}

    div[data-testid="stSegmentedControl"] button * {{
        color: inherit !important;
    }}

    div[data-testid="stSegmentedControl"] button[aria-checked="true"] {{
        background-color: var(--sh-surface) !important;
        color: var(--sh-text) !important;
        box-shadow: var(--sh-shadow-xs) !important;
        font-weight: 600 !important;
    }}

    div[data-testid="stSegmentedControl"] button[aria-checked="true"] * {{
        color: var(--sh-text) !important;
    }}

    /* File uploader */
    [data-testid="stFileUploader"] section[data-testid="stFileUploadDropzone"] {{
        background-color: var(--sh-surface-subtle) !important;
        border: 1.5px dashed var(--sh-border-strong) !important;
        border-radius: var(--sh-radius) !important;
    }}

    [data-testid="stFileUploader"] section[data-testid="stFileUploadDropzone"] * {{
        color: var(--sh-text-muted) !important;
    }}

    /* =========================================================
       CUSTOM UI PRIMITIVES
       ========================================================= */
    .sh-header-wrapper {{
        margin-bottom: 1.75rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid var(--sh-border-subtle);
    }}

    .sh-eyebrow {{
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--sh-primary);
        margin-bottom: 0.35rem;
    }}

    .sh-page-title {{
        font-size: 1.65rem;
        font-weight: 700;
        color: var(--sh-text);
        margin: 0 0 0.4rem 0;
        line-height: 1.25;
    }}

    .sh-page-desc {{
        font-size: 0.95rem;
        color: var(--sh-text-muted);
        line-height: 1.5;
        margin: 0;
    }}

    /* Badges */
    .sh-badge {{
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.2rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        line-height: 1.3;
    }}

    .sh-badge-success {{
        background-color: var(--sh-success-subtle);
        color: var(--sh-success);
        border: 1px solid var(--sh-success-border);
    }}

    .sh-badge-warning {{
        background-color: var(--sh-warning-subtle);
        color: var(--sh-warning);
        border: 1px solid var(--sh-warning-border);
    }}

    .sh-badge-primary {{
        background-color: var(--sh-primary-subtle);
        color: var(--sh-primary);
        border: 1px solid var(--sh-primary-border);
    }}

    .sh-badge-neutral {{
        background-color: var(--sh-surface-muted);
        color: var(--sh-text-muted);
        border: 1px solid var(--sh-border);
    }}

    .sh-badge-danger {{
        background-color: var(--sh-danger-subtle);
        color: var(--sh-danger);
        border: 1px solid var(--sh-danger-border);
    }}

    /* Skill chips */
    .sh-chip-container {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        margin: 0.35rem 0;
    }}

    .sh-chip {{
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.65rem;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 500;
        line-height: 1.2;
    }}

    .sh-chip-default {{
        background-color: var(--sh-chip-bg);
        color: var(--sh-chip-color);
        border: 1px solid var(--sh-chip-border);
    }}

    .sh-chip-matched {{
        background-color: var(--sh-primary-subtle);
        color: var(--sh-primary);
        border: 1px solid var(--sh-primary-border);
    }}

    .sh-chip-growth {{
        background-color: var(--sh-warning-subtle);
        color: var(--sh-warning);
        border: 1px solid var(--sh-warning-border);
    }}

    /* Comparison Card (Current vs Suggested) */
    .sh-compare-card {{
        background: var(--sh-surface);
        border: 1px solid var(--sh-border);
        border-radius: var(--sh-radius);
        padding: 1.15rem 1.25rem;
        margin-bottom: 1rem;
        box-shadow: var(--sh-shadow-xs);
    }}

    .sh-compare-label {{
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }}

    .sh-label-current {{
        color: var(--sh-text-muted);
    }}

    .sh-label-suggested {{
        color: var(--sh-primary);
    }}

    .sh-quote-text {{
        font-size: 0.9rem;
        line-height: 1.5;
        color: var(--sh-text);
        margin: 0 0 0.5rem 0;
    }}

    .sh-critique-note {{
        font-size: 0.8rem;
        color: var(--sh-warning);
        background: var(--sh-warning-subtle);
        padding: 0.35rem 0.65rem;
        border-radius: 4px;
        border: 1px solid var(--sh-warning-border);
        display: inline-block;
    }}

    /* Callout block */
    .sh-callout {{
        border-left: 3px solid var(--sh-primary);
        background-color: var(--sh-surface-subtle);
        padding: 0.85rem 1.15rem;
        border-radius: 0 var(--sh-radius-sm) var(--sh-radius-sm) 0;
        font-size: 0.875rem;
        line-height: 1.5;
        color: var(--sh-text);
        margin: 0.75rem 0;
    }}

    /* Metric card */
    .sh-metric-box {{
        background: var(--sh-surface);
        border: 1px solid var(--sh-border);
        border-radius: var(--sh-radius);
        padding: 1.15rem 1.25rem;
        box-shadow: var(--sh-shadow-xs);
    }}

    .sh-metric-label {{
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--sh-text-muted);
        margin-bottom: 0.35rem;
    }}

    .sh-metric-value {{
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--sh-text);
        line-height: 1.2;
    }}

    .sh-metric-caption {{
        font-size: 0.75rem;
        color: var(--sh-text-muted);
        margin-top: 0.35rem;
    }}

    /* Sidebar Brand Box */
    .sh-brand-container {{
        padding: 0.5rem 0 0.85rem 0;
        border-bottom: 1px solid var(--sh-border);
        margin-bottom: 1.1rem;
    }}

    .sh-brand-title {{
        font-size: 1.1rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: var(--sh-text);
        margin: 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }}

    .sh-brand-subtitle {{
        font-size: 0.75rem;
        font-weight: 500;
        color: var(--sh-primary);
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin: 0.15rem 0 0 0;
    }}

    /* Sidebar section label */
    .sh-nav-section-label {{
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--sh-text-muted);
        margin: 1.25rem 0 0.4rem 0.25rem;
    }}

    .sh-status-widget {{
        background: var(--sh-surface);
        border: 1px solid var(--sh-border);
        border-radius: var(--sh-radius);
        padding: 0.85rem;
        margin-top: 0.4rem;
        box-shadow: var(--sh-shadow-xs);
    }}
    </style>
    """
    st.html(css)


def render_page_header(eyebrow: str, title: str, description: str):
    """Renders the standardized 3-tier page header."""
    markup = f"""
    <div class="sh-header-wrapper">
        <div class="sh-eyebrow">{html.escape(eyebrow)}</div>
        <h1 class="sh-page-title">{html.escape(title)}</h1>
        <p class="sh-page-desc">{html.escape(description)}</p>
    </div>
    """
    st.html(markup)


def render_badge(text: str, variant: str = "neutral") -> str:
    """Returns HTML for a semantic badge."""
    v = variant.lower()
    if v in ("success", "confirmed", "approved"):
        cls = "sh-badge-success"
        icon = "&#10003; "
    elif v in ("warning", "review", "review required", "action needed"):
        cls = "sh-badge-warning"
        icon = "&#9679; "
    elif v in ("primary", "blue", "current", "active"):
        cls = "sh-badge-primary"
        icon = "&#9679; "
    elif v in ("danger", "error", "rejected"):
        cls = "sh-badge-danger"
        icon = "&#10005; "
    else:
        cls = "sh-badge-neutral"
        icon = "&#9675; "
    return f'<span class="sh-badge {cls}">{icon}{html.escape(text)}</span>'


def render_skill_chips_html(skills: List[str], variant: str = "default") -> str:
    """Returns HTML for a list of restrained skill chips."""
    if not skills:
        return '<span style="color: var(--sh-text-subtle); font-size: 0.8rem;">None specified</span>'
    cls = "sh-chip-default"
    if variant in ("matched", "success"):
        cls = "sh-chip-matched"
    elif variant in ("growth", "missing", "warning"):
        cls = "sh-chip-growth"

    chips_html = "".join([f'<span class="sh-chip {cls}">{html.escape(s)}</span>' for s in skills])
    return f'<div class="sh-chip-container">{chips_html}</div>'


def render_workflow_stepper(stages: List[Dict[str, Any]]):
    """
    Renders a responsive 5-stage stepper using 5 native Streamlit columns.
    Ensures all 5 stages render side-by-side in one row with theme-aware colors.
    """
    cols = st.columns(len(stages))
    for col, s in zip(cols, stages):
        state = s.get("state", "locked").lower()
        if state == "completed":
            badge_html = '<span class="sh-badge sh-badge-success" style="font-size: 0.65rem; padding: 0.1rem 0.4rem;">Done</span>'
            border_color = "var(--sh-success-border, #bbf7d0)"
            bg_color = "var(--sh-surface, #ffffff)"
            num_color = "var(--sh-success, #15803d)"
        elif state == "current":
            badge_html = '<span class="sh-badge sh-badge-primary" style="font-size: 0.65rem; padding: 0.1rem 0.4rem;">Current</span>'
            border_color = "var(--sh-primary, #1d4ed8)"
            bg_color = "var(--sh-surface, #ffffff)"
            num_color = "var(--sh-primary, #1d4ed8)"
        elif state == "available":
            badge_html = '<span class="sh-badge sh-badge-neutral" style="font-size: 0.65rem; padding: 0.1rem 0.4rem;">Available</span>'
            border_color = "var(--sh-border, #e2e8f0)"
            bg_color = "var(--sh-surface-subtle, #f8fafc)"
            num_color = "var(--sh-text-muted, #64748b)"
        else:
            badge_html = '<span class="sh-badge sh-badge-neutral" style="font-size: 0.65rem; padding: 0.1rem 0.4rem; opacity: 0.6;">Locked</span>'
            border_color = "var(--sh-border, #e2e8f0)"
            bg_color = "var(--sh-surface-subtle, #f8fafc)"
            num_color = "var(--sh-text-subtle, #94a3b8)"

        with col:
            st.html(f"""
            <div style="background: {bg_color}; border: 1.5px solid {border_color}; border-radius: 8px; padding: 0.75rem 0.85rem; min-height: 96px; display: flex; flex-direction: column; justify-content: space-between; box-shadow: var(--sh-shadow-xs);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                    <span style="font-size: 0.72rem; font-weight: 700; color: {num_color}; letter-spacing: 0.05em;">{html.escape(s.get('num', ''))}</span>
                    {badge_html}
                </div>
                <div style="font-size: 0.875rem; font-weight: 600; color: var(--sh-text); margin-bottom: 0.2rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                    {html.escape(s.get('title', ''))}
                </div>
                <div style="font-size: 0.75rem; color: var(--sh-text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                    {html.escape(s.get('caption', ''))}
                </div>
            </div>
            """)


def render_sidebar_brand():
    """Renders the top branding block in the sidebar."""
    html_content = """
    <div class="sh-brand-container">
        <div class="sh-brand-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--sh-primary)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <rect width="20" height="14" x="2" y="7" rx="2" ry="2"/>
                <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>
            </svg>
            SMART HIRE
        </div>
        <div class="sh-brand-subtitle">Career Intelligence</div>
    </div>
    """
    st.html(html_content)


def render_sidebar_status_widget(summary: Dict[str, Any]):
    """Renders the clean workflow status block in the sidebar with theme-aware text."""
    profile_badge = render_badge(summary["profile_status"], summary["profile_status"])
    target_role = summary.get("target_role", "Not specified")
    matched_count = summary.get("job_count", 0)

    html_content = f"""
    <div class="sh-status-widget">
        <div style="margin-bottom: 0.65rem;">{profile_badge}</div>
        <div style="font-size: 0.8rem; color: var(--sh-text-muted); margin-bottom: 0.25rem;">
            <strong style="color: var(--sh-text);">Target:</strong> {html.escape(target_role)}
        </div>
        <div style="font-size: 0.8rem; color: var(--sh-text-muted);">
            <strong style="color: var(--sh-text);">Matches:</strong> {matched_count} roles
        </div>
    </div>
    """
    st.html(html_content)


def render_metric_card(title: str, value: str, caption: str = ""):
    """Renders an enterprise SaaS KPI metric card."""
    caption_html = f'<div class="sh-metric-caption">{html.escape(caption)}</div>' if caption else ""
    card_html = f"""
    <div class="sh-metric-box">
        <div class="sh-metric-label">{html.escape(title)}</div>
        <div class="sh-metric-value">{html.escape(value)}</div>
        {caption_html}
    </div>
    """
    st.html(card_html)
