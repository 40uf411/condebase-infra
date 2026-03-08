import { clsx } from "@keycloakify/login-ui/tools/clsx";
import { useI18n } from "../../i18n";
import { kcSanitize } from "@keycloakify/login-ui/kcSanitize";
import { useKcContext } from "../../KcContext";
import { assert } from "tsafe/assert";

/** To use this component make sure that kcContext.social exists */
export function SocialProviders() {
    const { kcContext } = useKcContext();

    assert("social" in kcContext && kcContext.social !== undefined);

    const { msg } = useI18n();

    if (kcContext.social.providers === undefined || kcContext.social.providers.length === 0) {
        return null;
    }

    return (
        <div id="kc-social-providers" className="auth-console-social">
            <p className="auth-console-social-title">{msg("identity-provider-login-label")}</p>
            <ul className="auth-console-social-list">
                {kcContext.social.providers.map((...[p, , providers]) => (
                    <li key={p.alias}>
                        <a
                            id={`social-${p.alias}`}
                            className={clsx(
                                "auth-console-social-button",
                                providers.length > 3 && "auth-console-social-button-grid"
                            )}
                            type="button"
                            href={p.loginUrl}
                        >
                            {p.iconClasses && (
                                <i className={clsx("auth-console-social-icon", p.iconClasses)} aria-hidden="true"></i>
                            )}
                            <span
                                className={clsx("auth-console-social-name", p.iconClasses && "auth-console-social-name-with-icon")}
                                dangerouslySetInnerHTML={{
                                    __html: kcSanitize(p.displayName)
                                }}
                            />
                        </a>
                    </li>
                ))}
            </ul>
        </div>
    );
}
