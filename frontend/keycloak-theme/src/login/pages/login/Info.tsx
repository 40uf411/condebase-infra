import { assert } from "tsafe/assert";
import { useI18n } from "../../i18n";
import { useKcContext } from "../../KcContext";

export function Info() {
    const { kcContext } = useKcContext();
    assert(kcContext.pageId === "login.ftl");

    const { url } = kcContext;

    const { msg } = useI18n();

    return (
        <div className="auth-console-register-prompt" id="kc-registration-container">
            <span>
                {msg("noAccount")}{" "}
                <a tabIndex={8} className="auth-console-link" href={url.registrationUrl}>
                    {msg("doRegister")}
                </a>
            </span>
        </div>
    );
}
