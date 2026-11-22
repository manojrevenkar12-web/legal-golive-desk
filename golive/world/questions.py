"""Security-review questions customers send, with the evidence that truly answers each (None: no evidence exists, so
only the security team can answer). Phrasings vary and some arrive in German, as DACH questionnaires do."""

from __future__ import annotations

BANK: list[tuple[str | None, list[str]]] = [
    (
        "EV-ENC-REST",
        [
            "Is customer data encrypted at rest? Which algorithm?",
            "Describe encryption of stored data and key management.",
            "Werden gespeicherte Daten verschlüsselt? Wie werden Schlüssel verwaltet?",
        ],
    ),
    ("EV-ENC-TRANSIT", ["Which TLS versions are supported for data in transit?", "Is all traffic encrypted in transit?", "Welche TLS-Version wird für die Übertragung verwendet?"]),
    (
        "EV-SSO",
        [
            "Do you support SAML 2.0 single sign-on with our identity provider?",
            "Can users sign in with Entra ID (Azure AD)?",
            "Unterstützen Sie Single Sign-On über SAML oder OIDC?",
        ],
    ),
    ("EV-SCIM", ["How are leavers deprovisioned?", "Do you support SCIM user provisioning?", "Wie werden ausscheidende Mitarbeiter deprovisioniert?"]),
    ("EV-MFA", ["Is multi-factor authentication enforced?", "Do your staff use MFA for production access?"]),
    ("EV-RESIDENCY", ["Where will our data be stored and processed?", "Can data be hosted in Germany only?", "Wo werden unsere Daten gespeichert? Bitte Datenstandort angeben."]),
    ("EV-SUBPROC", ["Provide your list of subprocessors and how we are notified of changes.", "Welche Unterauftragsverarbeiter setzen Sie ein?"]),
    (
        "EV-NO-TRAIN",
        [
            "Do you use our data to train AI models?",
            "Will our documents be used to train the model provider's models?",
            "Werden unsere Daten zum Training von KI-Modellen verwendet?",
        ],
    ),
    ("EV-RETENTION", ["How long is data retained, and how is it deleted at contract end?", "Wie lange werden Daten nach Vertragsende aufbewahrt und wann gelöscht?"]),
    ("EV-PERMISSIONS", ["Are ethical walls from iManage respected?", "Will users see documents they cannot open in SharePoint?", "Werden Chinese Walls aus dem DMS übernommen?"]),
    ("EV-RBAC", ["Describe role-based access control for administrators.", "How is least privilege applied to your staff?"]),
    ("EV-AUDIT", ["Can we export audit logs to our SIEM?", "Which user actions are logged?"]),
    ("EV-ISO", ["Do you hold ISO 27001 certification?", "Sind Sie nach ISO 27001 zertifiziert?"]),
    ("EV-SOC2", ["Can you share a SOC 2 Type II report?"]),
    (
        "EV-PENTEST-2026",
        ["When was your last independent penetration test?", "Provide a summary of your latest penetration test.", "Wann wurde der letzte Penetrationstest durchgeführt?"],
    ),
    ("EV-VULN", ["What are your patching timelines for critical vulnerabilities?", "Describe vulnerability scanning in your build pipeline."]),
    (
        "EV-INCIDENT",
        ["How quickly are we notified of a personal data breach?", "Describe your incident response process.", "Wie schnell werden wir über einen Sicherheitsvorfall informiert?"],
    ),
    ("EV-BCDR", ["What are your RPO and RTO?", "Is disaster recovery tested?"]),
    ("EV-DPA", ["Do you sign a GDPR Article 28 data processing agreement?", "Bieten Sie einen AVV nach DSGVO an?"]),
    ("EV-STAFF", ["Are employees background checked?", "Do staff receive annual security training?"]),
    ("EV-AI-GOV", ["How do you evaluate model accuracy and hallucination risk?", "How do you prepare for the EU AI Act?"]),
    (
        None,
        [
            "Describe physical security controls at your data centres.",
            "Do you hold cyber insurance, and for what amount?",
            "Can we audit your premises on site?",
            "Do you comply with the BRAO and § 203 StGB professional secrecy rules?",
            "Is the product certified under BSI C5?",
            "Name the employees who can access our matters.",
        ],
    ),
]


GERMAN_STARTS = ("Werden", "Wo ", "Wie ", "Welche", "Sind ", "Bieten", "Wann", "Unterstützen")


def is_german(question: str) -> bool:
    return question.startswith(GERMAN_STARTS)
