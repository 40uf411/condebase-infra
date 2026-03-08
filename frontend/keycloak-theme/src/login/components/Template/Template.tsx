import type { ReactNode } from "react";
import { useEffect } from "react";
import { clsx } from "@keycloakify/login-ui/tools/clsx";
import { kcSanitize } from "@keycloakify/login-ui/kcSanitize";
import { useSetClassName } from "@keycloakify/login-ui/tools/useSetClassname";
import { useInitializeTemplate } from "./useInitializeTemplate";
import { useI18n } from "../../i18n";
import { useKcContext } from "../../KcContext";

export function Template(props: {
    displayInfo?: boolean;
    displayMessage?: boolean;
    displayRequiredFields?: boolean;
    headerNode: ReactNode;
    socialProvidersNode?: ReactNode;
    infoNode?: ReactNode;
    documentTitle?: string;
    bodyClassName?: string;
    children: ReactNode;
}) {
    const {
        displayInfo = false,
        displayMessage = true,
        displayRequiredFields = false,
        headerNode,
        socialProvidersNode = null,
        infoNode = null,
        documentTitle,
        bodyClassName,
        children
    } = props;

    const { kcContext } = useKcContext();

    const { msg, msgStr, currentLanguage, enabledLanguages } = useI18n();

    useEffect(() => {
        document.title =
            documentTitle ?? msgStr("loginTitle", kcContext.realm.displayName || kcContext.realm.name);
    }, []);

    useSetClassName({
        qualifiedName: "html",
        className: "auth-console-html"
    });

    useSetClassName({
        qualifiedName: "body",
        className: bodyClassName ?? "auth-console-body"
    });

    const { isReadyToRender } = useInitializeTemplate();

    if (!isReadyToRender) {
        return null;
    }

    return (
        <div className="auth-console-root">
            <div className="auth-console-orb auth-console-orb-1" />
            <div className="auth-console-orb auth-console-orb-2" />
            <div className="auth-console-orb auth-console-orb-3" />

            <main className="auth-console-shell">
                <section className="auth-console-hero">
                    <p className="auth-console-eyebrow">Auth Profile Console</p>
                    <h1 className="auth-console-brand">
                        {msg("loginTitleHtml", kcContext.realm.displayNameHtml || kcContext.realm.name)}
                    </h1>
                    <p className="auth-console-subtitle">
                        Sign in securely and manage your account access.
                    </p>

                    {enabledLanguages.length > 1 && (
                        <div className="auth-console-locale-wrap" id="kc-locale">
                            <div id="kc-locale-wrapper">
                                <div
                                    id="kc-locale-dropdown"
                                    className={clsx("menu-button-links", "auth-console-locale-dropdown")}
                                >
                                    <button
                                        tabIndex={1}
                                        id="kc-current-locale-link"
                                        aria-label={msgStr("languages")}
                                        aria-haspopup="true"
                                        aria-expanded="false"
                                        aria-controls="language-switch1"
                                    >
                                        {currentLanguage.label}
                                    </button>
                                    <ul
                                        role="menu"
                                        tabIndex={-1}
                                        aria-labelledby="kc-current-locale-link"
                                        aria-activedescendant=""
                                        id="language-switch1"
                                        className="auth-console-locale-list"
                                    >
                                        {enabledLanguages.map(({ languageTag, label, href }, i) => (
                                            <li key={languageTag} role="none">
                                                <a role="menuitem" id={`language-${i + 1}`} href={href}>
                                                    {label}
                                                </a>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        </div>
                    )}
                </section>

                <section className="auth-console-panel">
                    <header className="auth-console-panel-header">
                        {!(kcContext.auth !== undefined &&
                            kcContext.auth.showUsername &&
                            !kcContext.auth.showResetCredentials) ? (
                            <h2 id="kc-page-title">{headerNode}</h2>
                        ) : (
                            <div className="auth-console-userbox">
                                <label id="kc-attempted-username">{kcContext.auth.attemptedUsername}</label>
                                <a
                                    id="reset-login"
                                    href={kcContext.url.loginRestartFlowUrl}
                                    aria-label={msgStr("restartLoginTooltip")}
                                >
                                    {msg("restartLoginTooltip")}
                                </a>
                            </div>
                        )}

                        {displayRequiredFields && (
                            <p className="auth-console-required-hint">
                                <span>*</span> {msg("requiredFields")}
                            </p>
                        )}
                    </header>

                    {displayMessage &&
                        kcContext.message !== undefined &&
                        (kcContext.message.type !== "warning" || !kcContext.isAppInitiatedAction) && (
                            <div className={clsx("auth-console-alert", `auth-console-alert-${kcContext.message.type}`)}>
                                <span
                                    dangerouslySetInnerHTML={{
                                        __html: kcSanitize(kcContext.message.summary)
                                    }}
                                />
                            </div>
                        )}

                    <div className="auth-console-panel-content">{children}</div>

                    {kcContext.auth !== undefined && kcContext.auth.showTryAnotherWayLink && (
                        <form
                            id="kc-select-try-another-way-form"
                            action={kcContext.url.loginAction}
                            method="post"
                            className="auth-console-alt-auth-form"
                        >
                            <input type="hidden" name="tryAnotherWay" value="on" />
                            <button
                                type="button"
                                className="auth-console-link-button"
                                onClick={event => {
                                    event.preventDefault();
                                    document.forms[
                                        "kc-select-try-another-way-form" as never
                                    ].requestSubmit();
                                }}
                            >
                                {msg("doTryAnotherWay")}
                            </button>
                        </form>
                    )}

                    {socialProvidersNode !== null && (
                        <div className="auth-console-social-slot">{socialProvidersNode}</div>
                    )}

                    {displayInfo && (
                        <div id="kc-info" className="auth-console-info-slot">
                            {infoNode}
                        </div>
                    )}
                </section>
            </main>
        </div>
    );
}
