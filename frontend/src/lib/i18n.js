"use client";

/**
 * Minimal bilingual support for BharatCompliance client app.
 * Covers English (en) and Hindi (hi).
 *
 * Usage:
 *   const { t, lang, setLang } = useLang();
 *   <p>{t("home.greeting_morning")}</p>
 */

import { useState, useEffect } from "react";

const LANG_KEY = "bc_lang";

const translations = {
  en: {
    // Nav
    "nav.home":       "Home",
    "nav.add":        "Add",
    "nav.history":    "History",
    "nav.receipts":   "Receipts",
    "nav.deadlines":  "Deadlines",

    // Greetings
    "home.greeting_morning":   "Good morning",
    "home.greeting_afternoon": "Good afternoon",
    "home.greeting_evening":   "Good evening",
    "home.date_prefix":        "",

    // Home summary
    "home.net_income":    "Net Income",
    "home.sales":         "Sales",
    "home.expenses":      "Expenses",
    "home.entries":       "entries",
    "home.profit_margin": "Profit margin",
    "home.add_sale":      "Add Sale",
    "home.add_expense":   "Add Expense",
    "home.record_income": "Record income",
    "home.record_purchase":"Record purchase",
    "home.action_required":"Action Required",
    "home.recent_entries": "Recent Entries",
    "home.all":            "All",
    "home.no_entries":     "No entries yet",
    "home.no_entries_sub": "Start recording your sales and expenses to track your finances.",
    "home.add_first":      "Add First Entry",
    "home.view_all":       "View all",
    "home.activity":       "Daily Activity",
    "home.expense_by_cat": "Expenses by Category",

    // Score page
    "score.title":        "My Score",
    "score.compliance":   "Compliance Score",
    "score.grade":        "Grade",
    "score.evidence":     "Evidence Health",
    "score.gst_risk":     "GST Risk",
    "score.managed_by":   "Managed by",
    "score.share_wa":     "Share on WhatsApp",
    "score.share":        "Share Card",
    "score.last_updated": "Last updated",
    "score.grade_a":      "Excellent",
    "score.grade_b":      "Good",
    "score.grade_c":      "Needs Attention",
    "score.grade_d":      "Critical",
    "score.gst_low":      "Low Risk",
    "score.gst_medium":   "Medium Risk",
    "score.gst_high":     "High Risk",
    "score.share_msg":    "My BharatCompliance score is {score}/100 (Grade {grade}) — keeping my books clean! 📊",

    // Annual report
    "report.title":         "Annual Report",
    "report.download":      "Download PDF",
    "report.year":          "Year",
    "report.month":         "Month",
    "report.sales":         "Sales",
    "report.expenses":      "Expenses",
    "report.net":           "Net Income",
    "report.entries":       "Entries",
    "report.total":         "Total",
    "report.generated":     "Generated on",
    "report.powered_by":    "Powered by BharatCompliance",

    // Transactions
    "tx.add_sale":    "Record a Sale",
    "tx.add_expense": "Record an Expense",
    "tx.amount":      "Amount (₹)",
    "tx.description": "Description",
    "tx.date":        "Date",
    "tx.category":    "Category",
    "tx.add_photo":   "Add Receipt Photo",
    "tx.save":        "Save Entry",

    // Profile
    "profile.title":       "My Profile",
    "profile.change_pin":  "Change PIN",
    "profile.current_pin": "Current PIN",
    "profile.new_pin":     "New PIN",
    "profile.confirm_pin": "Confirm PIN",
    "profile.save":        "Save Changes",
    "profile.language":    "Language",
    "profile.english":     "English",
    "profile.hindi":       "हिंदी",
    "profile.logout":      "Log out",

    // Deadlines
    "deadline.title":    "My Deadlines",
    "deadline.pending":  "Pending",
    "deadline.done":     "Done",
    "deadline.overdue":  "Overdue",
    "deadline.ack":      "Acknowledge",

    // Common
    "common.loading": "Loading…",
    "common.error":   "Something went wrong.",
    "common.retry":   "Retry",
    "common.save":    "Save",
    "common.cancel":  "Cancel",
    "common.close":   "Close",
  },

  hi: {
    // Nav
    "nav.home":      "होम",
    "nav.add":       "जोड़ें",
    "nav.history":   "इतिहास",
    "nav.receipts":  "रसीदें",
    "nav.deadlines": "समय-सीमा",

    // Greetings
    "home.greeting_morning":   "सुप्रभात",
    "home.greeting_afternoon": "नमस्कार",
    "home.greeting_evening":   "शुभ संध्या",
    "home.date_prefix":        "",

    // Home summary
    "home.net_income":     "शुद्ध आय",
    "home.sales":          "बिक्री",
    "home.expenses":       "खर्च",
    "home.entries":        "प्रविष्टियाँ",
    "home.profit_margin":  "लाभ मार्जिन",
    "home.add_sale":       "बिक्री जोड़ें",
    "home.add_expense":    "खर्च जोड़ें",
    "home.record_income":  "आय दर्ज करें",
    "home.record_purchase":"खरीद दर्ज करें",
    "home.action_required":"कार्रवाई ज़रूरी",
    "home.recent_entries": "हाल की प्रविष्टियाँ",
    "home.all":            "सभी",
    "home.no_entries":     "अभी कोई प्रविष्टि नहीं",
    "home.no_entries_sub": "अपनी बिक्री और खर्च दर्ज करके वित्त को ट्रैक करें।",
    "home.add_first":      "पहली प्रविष्टि जोड़ें",
    "home.view_all":       "सभी देखें",
    "home.activity":       "दैनिक गतिविधि",
    "home.expense_by_cat": "श्रेणी के अनुसार खर्च",

    // Score page
    "score.title":        "मेरा स्कोर",
    "score.compliance":   "अनुपालन स्कोर",
    "score.grade":        "ग्रेड",
    "score.evidence":     "साक्ष्य स्वास्थ्य",
    "score.gst_risk":     "जीएसटी जोखिम",
    "score.managed_by":   "प्रबंधित है",
    "score.share_wa":     "WhatsApp पर शेयर करें",
    "score.share":        "कार्ड शेयर करें",
    "score.last_updated": "अंतिम अपडेट",
    "score.grade_a":      "उत्कृष्ट",
    "score.grade_b":      "अच्छा",
    "score.grade_c":      "ध्यान दें",
    "score.grade_d":      "गंभीर",
    "score.gst_low":      "कम जोखिम",
    "score.gst_medium":   "मध्यम जोखिम",
    "score.gst_high":     "उच्च जोखिम",
    "score.share_msg":    "मेरा BharatCompliance स्कोर {score}/100 (ग्रेड {grade}) है — हिसाब-किताब साफ रख रहा हूँ! 📊",

    // Annual report
    "report.title":      "वार्षिक रिपोर्ट",
    "report.download":   "PDF डाउनलोड करें",
    "report.year":       "वर्ष",
    "report.month":      "महीना",
    "report.sales":      "बिक्री",
    "report.expenses":   "खर्च",
    "report.net":        "शुद्ध आय",
    "report.entries":    "प्रविष्टियाँ",
    "report.total":      "कुल",
    "report.generated":  "पर बनाया गया",
    "report.powered_by": "BharatCompliance द्वारा संचालित",

    // Transactions
    "tx.add_sale":    "बिक्री दर्ज करें",
    "tx.add_expense": "खर्च दर्ज करें",
    "tx.amount":      "राशि (₹)",
    "tx.description": "विवरण",
    "tx.date":        "तारीख",
    "tx.category":    "श्रेणी",
    "tx.add_photo":   "रसीद फोटो जोड़ें",
    "tx.save":        "प्रविष्टि सहेजें",

    // Profile
    "profile.title":       "मेरी प्रोफाइल",
    "profile.change_pin":  "PIN बदलें",
    "profile.current_pin": "वर्तमान PIN",
    "profile.new_pin":     "नया PIN",
    "profile.confirm_pin": "PIN की पुष्टि करें",
    "profile.save":        "बदलाव सहेजें",
    "profile.language":    "भाषा",
    "profile.english":     "English",
    "profile.hindi":       "हिंदी",
    "profile.logout":      "लॉग आउट",

    // Deadlines
    "deadline.title":    "मेरी समय-सीमाएँ",
    "deadline.pending":  "बाकी",
    "deadline.done":     "हो गया",
    "deadline.overdue":  "देर हो गई",
    "deadline.ack":      "स्वीकार करें",

    // Common
    "common.loading": "लोड हो रहा है…",
    "common.error":   "कुछ गलत हो गया।",
    "common.retry":   "पुनः प्रयास",
    "common.save":    "सहेजें",
    "common.cancel":  "रद्द करें",
    "common.close":   "बंद करें",
  },
};

/** Read stored language, default to "en". */
export function getStoredLang() {
  if (typeof window === "undefined") return "en";
  return localStorage.getItem(LANG_KEY) || "en";
}

/** Persist language choice. */
export function storeLang(lang) {
  if (typeof window !== "undefined") localStorage.setItem(LANG_KEY, lang);
}

/**
 * Translate a key, with optional {variable} interpolation.
 *
 * t("score.share_msg", { score: 87, grade: "A" })
 * → "My BharatCompliance score is 87/100 (Grade A) …"
 */
export function translate(lang, key, vars = {}) {
  const dict = translations[lang] || translations.en;
  let str = dict[key] ?? translations.en[key] ?? key;
  Object.entries(vars).forEach(([k, v]) => {
    str = str.replaceAll(`{${k}}`, v);
  });
  return str;
}

/**
 * React hook — returns { t, lang, setLang }.
 * Re-renders the component whenever the language changes.
 */
export function useLang() {
  const [lang, setLangState] = useState("en");

  useEffect(() => {
    setLangState(getStoredLang());
  }, []);

  const setLang = (next) => {
    storeLang(next);
    setLangState(next);
  };

  const t = (key, vars) => translate(lang, key, vars);

  return { t, lang, setLang };
}
