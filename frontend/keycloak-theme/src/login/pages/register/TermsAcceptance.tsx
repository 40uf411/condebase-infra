import { kcSanitize } from "@keycloakify/login-ui/kcSanitize";
import { useKcContext } from "../../KcContext";
import { useI18n } from "../../i18n";

export function TermsAcceptance(props: {
    areTermsAccepted: boolean;
    onAreTermsAcceptedValueChange: (areTermsAccepted: boolean) => void;
}) {
    const { areTermsAccepted, onAreTermsAcceptedValueChange } = props;

    const { kcContext } = useKcContext();
    const { msg } = useI18n();

    return (
        <>
            <div className="auth-console-terms">
                <p className="auth-console-terms-title">{msg("termsTitle")}</p>
                <div id="kc-registration-terms-text" className="auth-console-terms-text">
                    {msg("termsText")}
                </div>
            </div>
            <div className="auth-console-group">
                <label className="auth-console-checkbox" htmlFor="termsAccepted">
                    <input
                        type="checkbox"
                        id="termsAccepted"
                        name="termsAccepted"
                        className="auth-console-checkbox-input"
                        checked={areTermsAccepted}
                        onChange={e => onAreTermsAcceptedValueChange(e.target.checked)}
                        aria-invalid={kcContext.messagesPerField.existsError("termsAccepted")}
                    />
                    <span>{msg("acceptTerms")}</span>
                </label>

                {kcContext.messagesPerField.existsError("termsAccepted") && (
                    <span
                        id="input-error-terms-accepted"
                        className="auth-console-field-error"
                        aria-live="polite"
                        dangerouslySetInnerHTML={{
                            __html: kcSanitize(kcContext.messagesPerField.get("termsAccepted"))
                        }}
                    />
                )}
            </div>
        </>
    );
}
