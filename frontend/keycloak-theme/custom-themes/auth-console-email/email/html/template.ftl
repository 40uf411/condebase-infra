<#macro emailLayout>
<!DOCTYPE html>
<html lang="${locale.language}" dir="${(ltr)?then('ltr','rtl')}">
<head>
    <meta charset="UTF-8" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta name="viewport" content="width=device-width,initial-scale=1.0" />
    <title>${realmName!'Auth Console'}</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            background-color: #f7f4ea;
            background-image:
                radial-gradient(circle at 18% 15%, #f3eac3 0%, transparent 34%),
                radial-gradient(circle at 85% 20%, #dbf7f2 0%, transparent 40%),
                linear-gradient(130deg, #f7f4ea, #efe9d6);
            color: #1f2937;
            font-family: "Sora", "Trebuchet MS", "Segoe UI", Arial, sans-serif;
        }

        .kc-shell {
            width: 100%;
            max-width: 700px;
            margin: 0 auto;
            border: 1px solid rgba(15, 118, 110, 0.2);
            border-radius: 24px;
            overflow: hidden;
            background: #fffdf6;
            box-shadow: 0 18px 42px rgba(15, 23, 42, 0.12);
        }

        .kc-hero {
            padding: 24px 28px;
            border-bottom: 1px solid rgba(15, 118, 110, 0.18);
            background: linear-gradient(135deg, rgba(15, 118, 110, 0.18), rgba(221, 107, 32, 0.15));
        }

        .kc-eyebrow {
            margin: 0 0 8px;
            color: #334155;
            font-size: 12px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            font-weight: 700;
        }

        .kc-brand {
            margin: 0;
            color: #0f766e;
            font-size: 28px;
            line-height: 1.2;
            font-weight: 700;
        }

        .kc-subtitle {
            margin: 8px 0 0;
            color: #334155;
            font-size: 14px;
        }

        .kc-content {
            padding: 24px 28px;
            color: #1f2937;
            font-size: 15px;
            line-height: 1.65;
        }

        .kc-content p {
            margin: 0 0 14px;
        }

        .kc-content p:last-child {
            margin-bottom: 0;
        }

        .kc-content a {
            color: #0f766e;
            font-weight: 600;
        }

        .kc-content p a {
            display: inline-block;
            text-decoration: none;
            background: #0f766e;
            color: #f8fffe !important;
            border-radius: 999px;
            padding: 10px 18px;
            margin-top: 4px;
        }

        .kc-content p a:hover {
            background: #115e59;
        }

        .kc-footer {
            padding: 14px 28px 20px;
            border-top: 1px solid rgba(15, 118, 110, 0.12);
            color: #64748b;
            font-size: 12px;
            line-height: 1.5;
        }

        @media screen and (max-width: 640px) {
            .kc-shell {
                border-radius: 16px;
            }

            .kc-hero,
            .kc-content,
            .kc-footer {
                padding-left: 16px;
                padding-right: 16px;
            }

            .kc-brand {
                font-size: 22px;
            }
        }
    </style>
</head>
<body>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
        <tr>
            <td align="center" style="padding: 28px 12px;">
                <table role="presentation" class="kc-shell" width="100%" cellspacing="0" cellpadding="0" border="0">
                    <tr>
                        <td class="kc-hero">
                            <p class="kc-eyebrow">${msg("emailThemeEyebrow")}</p>
                            <h1 class="kc-brand">${realmName!'Auth Console'}</h1>
                            <p class="kc-subtitle">${msg("emailThemeSubtitle")}</p>
                        </td>
                    </tr>
                    <tr>
                        <td class="kc-content">
                            <#nested>
                        </td>
                    </tr>
                    <tr>
                        <td class="kc-footer">
                            ${msg("emailThemeFooter", realmName!'Auth Console')}
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
</#macro>
