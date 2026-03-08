import { useState } from "react";
import { assert } from "tsafe/assert";
import { useI18n } from "../../i18n";
import { useKcContext } from "../../KcContext";
import { kcSanitize } from "@keycloakify/login-ui/kcSanitize";
import { useScript } from "./useScript";
import { useIsPasswordRevealed } from "@keycloakify/login-ui/tools/useIsPasswordRevealed";

export function Form() {
    const { kcContext } = useKcContext();
    assert(kcContext.pageId === "login.ftl");

    const { msg, msgStr } = useI18n();

    const [isLoginButtonDisabled, setIsLoginButtonDisabled] = useState(false);

    const webAuthnButtonId = "authenticateWebAuthnButton";
    const passwordInputId = "password";
    const { isPasswordRevealed, toggleIsPasswordRevealed } = useIsPasswordRevealed({
        passwordInputId
    });

    useScript({ webAuthnButtonId });

    return (
        <>
            {kcContext.realm.password && (
                <form
                    id="kc-form-login"
                    className="auth-console-form"
                    onSubmit={() => {
                        setIsLoginButtonDisabled(true);
                        return true;
                    }}
                    action={kcContext.url.loginAction}
                    method="post"
                >
                    {!kcContext.usernameHidden && (
                        <div className="auth-console-group">
                            <label htmlFor="username" className="auth-console-label">
                                {!kcContext.realm.loginWithEmailAllowed
                                    ? msg("username")
                                    : !kcContext.realm.registrationEmailAsUsername
                                      ? msg("usernameOrEmail")
                                      : msg("email")}
                            </label>
                            <input
                                tabIndex={2}
                                id="username"
                                className="auth-console-input"
                                name="username"
                                defaultValue={kcContext.login.username ?? ""}
                                type="text"
                                autoFocus
                                autoComplete={
                                    kcContext.enableWebAuthnConditionalUI
                                        ? "username webauthn"
                                        : "username"
                                }
                                aria-invalid={kcContext.messagesPerField.existsError(
                                    "username",
                                    "password"
                                )}
                            />
                        </div>
                    )}

                    <div className="auth-console-group">
                        <label htmlFor={passwordInputId} className="auth-console-label">
                            {msg("password")}
                        </label>
                        <div className="auth-console-password-wrap">
                            <input
                                tabIndex={3}
                                id={passwordInputId}
                                className="auth-console-input"
                                name="password"
                                type={isPasswordRevealed ? "text" : "password"}
                                autoComplete="current-password"
                                aria-invalid={kcContext.messagesPerField.existsError(
                                    "username",
                                    "password"
                                )}
                            />
                            <button
                                type="button"
                                className="auth-console-password-toggle"
                                aria-label={msgStr(isPasswordRevealed ? "hidePassword" : "showPassword")}
                                aria-controls={passwordInputId}
                                onClick={toggleIsPasswordRevealed}
                            >
                                {isPasswordRevealed ? msg("hidePassword") : msg("showPassword")}
                            </button>
                        </div>
                    </div>

                    {kcContext.messagesPerField.existsError("username", "password") && (
                        <p
                            id="input-error"
                            className="auth-console-field-error"
                            aria-live="polite"
                            dangerouslySetInnerHTML={{
                                __html: kcSanitize(
                                    kcContext.messagesPerField.getFirstError("username", "password")
                                )
                            }}
                        />
                    )}

                    <div className="auth-console-options-row">
                        <div>
                            {kcContext.realm.rememberMe && !kcContext.usernameHidden && (
                                <label className="auth-console-checkbox">
                                    <input
                                        tabIndex={5}
                                        id="rememberMe"
                                        name="rememberMe"
                                        type="checkbox"
                                        defaultChecked={!!kcContext.login.rememberMe}
                                    />
                                    <span>{msg("rememberMe")}</span>
                                </label>
                            )}
                        </div>

                        <div>
                            {kcContext.realm.resetPasswordAllowed && (
                                <a tabIndex={6} className="auth-console-link" href={kcContext.url.loginResetCredentialsUrl}>
                                    {msg("doForgotPassword")}
                                </a>
                            )}
                        </div>
                    </div>

                    <div className="auth-console-actions">
                        <input
                            type="hidden"
                            id="id-hidden-input"
                            name="credentialId"
                            value={kcContext.auth.selectedCredential}
                        />
                        <input
                            tabIndex={7}
                            disabled={isLoginButtonDisabled}
                            className="auth-console-btn auth-console-btn-primary auth-console-btn-block"
                            name="login"
                            id="kc-login"
                            type="submit"
                            value={msgStr("doLogIn")}
                        />
                    </div>
                </form>
            )}

            {kcContext.enableWebAuthnConditionalUI && (
                <>
                    <form id="webauth" action={kcContext.url.loginAction} method="post">
                        <input type="hidden" id="clientDataJSON" name="clientDataJSON" />
                        <input type="hidden" id="authenticatorData" name="authenticatorData" />
                        <input type="hidden" id="signature" name="signature" />
                        <input type="hidden" id="credentialId" name="credentialId" />
                        <input type="hidden" id="userHandle" name="userHandle" />
                        <input type="hidden" id="error" name="error" />
                    </form>
                    {kcContext.authenticators !== undefined &&
                        kcContext.authenticators.authenticators.length !== 0 && (
                            <form id="authn_select">
                                {kcContext.authenticators.authenticators.map((authenticator, i) => (
                                    <input
                                        key={i}
                                        type="hidden"
                                        name="authn_use_chk"
                                        readOnly
                                        value={authenticator.credentialId}
                                    />
                                ))}
                            </form>
                        )}
                    <div className="auth-console-passkey-wrap">
                        <input
                            id={webAuthnButtonId}
                            type="button"
                            className="auth-console-btn auth-console-btn-secondary auth-console-btn-block"
                            value={msgStr("passkey-doAuthenticate")}
                        />
                    </div>
                </>
            )}
        </>
    );
}
