import type { JSX } from "@keycloakify/login-ui/tools/JSX";
import { useIsPasswordRevealed } from "@keycloakify/login-ui/tools/useIsPasswordRevealed";
import { useI18n } from "../i18n";

export function PasswordWrapper(props: { passwordInputId: string; children: JSX.Element }) {
    const { passwordInputId, children } = props;

    const { msgStr } = useI18n();

    const { isPasswordRevealed, toggleIsPasswordRevealed } = useIsPasswordRevealed({
        passwordInputId
    });

    return (
        <div className="auth-console-password-wrap">
            {children}
            <button
                type="button"
                className="auth-console-password-toggle"
                aria-label={msgStr(isPasswordRevealed ? "hidePassword" : "showPassword")}
                aria-controls={passwordInputId}
                onClick={toggleIsPasswordRevealed}
            >
                {msgStr(isPasswordRevealed ? "hidePassword" : "showPassword")}
            </button>
        </div>
    );
}
