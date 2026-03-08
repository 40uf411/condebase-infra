import { useEffect, useLayoutEffect, useMemo, useState } from "react";
import { assert } from "tsafe/assert";
import { clsx } from "@keycloakify/login-ui/tools/clsx";
import { useKcContext } from "../../KcContext";
import { useI18n } from "../../i18n";
import { UserProfileFormFields } from "../../components/UserProfileFormFields";
import { TermsAcceptance } from "./TermsAcceptance";
import type { Attribute } from "@keycloakify/login-ui/KcContext";

type StepKey = "identity" | "details" | "security";

const IDENTITY_FIELDS = new Set(["firstname", "lastname", "username", "email"]);

function isSecurityAttribute(attribute: Attribute): boolean {
    const attributeName = attribute.name.toLowerCase();

    return attributeName === "password" || attributeName === "password-confirm" || attributeName.includes("password");
}

function isIdentityAttribute(attribute: Attribute): boolean {
    return IDENTITY_FIELDS.has(attribute.name.toLowerCase());
}

export function Form() {
    const { kcContext } = useKcContext();
    assert(kcContext.pageId === "register.ftl");
    const { msg } = useI18n();

    const [isFormSubmittable, setIsFormSubmittable] = useState(false);
    const [areTermsAccepted, setAreTermsAccepted] = useState(false);
    const [currentStepIndex, setCurrentStepIndex] = useState(0);

    const profileAttributes = useMemo<Attribute[]>(() => {
        if (!("profile" in kcContext) || kcContext.profile === undefined) {
            return [];
        }

        const profile = kcContext.profile as {
            attributes?: Attribute[];
            attributesByName?: Record<string, Attribute>;
        };

        if (Array.isArray(profile.attributes) && profile.attributes.length > 0) {
            return profile.attributes;
        }

        if (profile.attributesByName !== undefined) {
            return Object.values(profile.attributesByName);
        }

        return [];
    }, [kcContext]);

    const hasDetailsStep = useMemo(
        () =>
            profileAttributes.some(attribute => {
                if (attribute.annotations?.inputType === "hidden") {
                    return false;
                }

                return !isIdentityAttribute(attribute) && !isSecurityAttribute(attribute);
            }),
        [profileAttributes]
    );

    const steps = useMemo(
        () =>
            [
                { key: "identity" as const, label: "Account basics" },
                ...(hasDetailsStep ? [{ key: "details" as const, label: "Additional details" }] : []),
                { key: "security" as const, label: "Security" }
            ] satisfies ReadonlyArray<{ key: StepKey; label: string }>,
        [hasDetailsStep]
    );

    useEffect(() => {
        setCurrentStepIndex(previousStepIndex => Math.min(previousStepIndex, steps.length - 1));
    }, [steps.length]);

    const currentStep = steps[currentStepIndex];
    const isFirstStep = currentStepIndex === 0;
    const isLastStep = currentStepIndex === steps.length - 1;

    const isFieldVisible = (attribute: Attribute) => {
        if (attribute.annotations?.inputType === "hidden") {
            return true;
        }

        switch (currentStep.key) {
            case "identity":
                return isIdentityAttribute(attribute);
            case "details":
                return !isIdentityAttribute(attribute) && !isSecurityAttribute(attribute);
            case "security":
                return isSecurityAttribute(attribute);
        }
    };

    const hasVisibleFieldsInCurrentStep = (() => {
        if (currentStep.key === "security") {
            return true;
        }

        if (profileAttributes.length === 0) {
            return currentStep.key === "identity";
        }

        return profileAttributes.some(attribute => {
            if (attribute.annotations?.inputType === "hidden") {
                return false;
            }

            return isFieldVisible(attribute);
        });
    })();

    const goToNextStep = () => {
        setCurrentStepIndex(previousStepIndex => Math.min(previousStepIndex + 1, steps.length - 1));
    };

    const goToPreviousStep = () => {
        setCurrentStepIndex(previousStepIndex => Math.max(previousStepIndex - 1, 0));
    };

    useLayoutEffect(() => {
        (window as any)["onSubmitRecaptcha"] = () => {
            // @ts-expect-error
            document.getElementById("kc-register-form").requestSubmit();
        };

        return () => {
            delete (window as any)["onSubmitRecaptcha"];
        };
    }, []);

    return (
        <form
            id="kc-register-form"
            className="auth-console-form auth-console-register-form"
            action={kcContext.url.registrationAction}
            method="post"
            onSubmit={event => {
                if (!isLastStep) {
                    event.preventDefault();
                    goToNextStep();
                }
            }}
        >
            <div className="auth-console-stepper" aria-label="Registration steps">
                {steps.map((step, index) => (
                    <div
                        key={step.key}
                        className={clsx(
                            "auth-console-step",
                            index === currentStepIndex && "auth-console-step-active",
                            index < currentStepIndex && "auth-console-step-complete"
                        )}
                    >
                        <span className="auth-console-step-number">{index + 1}</span>
                        <span>{step.label}</span>
                    </div>
                ))}
            </div>

            <div className="auth-console-step-headline">
                <p className="auth-console-step-meta">
                    Step {currentStepIndex + 1} of {steps.length}
                </p>
                <h3>{currentStep.label}</h3>
            </div>

            <div className="auth-console-register-fields">
                {!hasVisibleFieldsInCurrentStep && (
                    <p className="auth-console-step-empty">No extra fields are required in this step.</p>
                )}
                <UserProfileFormFields
                    onIsFormSubmittableValueChange={setIsFormSubmittable}
                    isFieldVisible={isFieldVisible}
                />
            </div>

            {isLastStep && kcContext.termsAcceptanceRequired && (
                <TermsAcceptance
                    areTermsAccepted={areTermsAccepted}
                    onAreTermsAcceptedValueChange={setAreTermsAccepted}
                />
            )}

            {isLastStep &&
                kcContext.recaptchaRequired &&
                (kcContext.recaptchaVisible || kcContext.recaptchaAction === undefined) && (
                    <div className="auth-console-group">
                        <div
                            className="g-recaptcha"
                            data-size="compact"
                            data-sitekey={kcContext.recaptchaSiteKey}
                            data-action={kcContext.recaptchaAction}
                        ></div>
                    </div>
                )}

            <div className="auth-console-nav">
                <div className="auth-console-nav-left">
                    {!isFirstStep && (
                        <button
                            type="button"
                            className="auth-console-btn auth-console-btn-secondary"
                            onClick={goToPreviousStep}
                        >
                            Back
                        </button>
                    )}
                </div>

                <div className="auth-console-nav-right">
                    {!isLastStep && (
                        <button
                            type="button"
                            className="auth-console-btn auth-console-btn-primary"
                            onClick={goToNextStep}
                        >
                            Next
                        </button>
                    )}

                    {isLastStep &&
                        (kcContext.recaptchaRequired &&
                        !kcContext.recaptchaVisible &&
                        kcContext.recaptchaAction !== undefined ? (
                            <button
                                className={clsx("auth-console-btn auth-console-btn-primary g-recaptcha")}
                                data-sitekey={kcContext.recaptchaSiteKey}
                                data-callback="onSubmitRecaptcha"
                                data-action={kcContext.recaptchaAction}
                                type="submit"
                                disabled={
                                    !isFormSubmittable ||
                                    (kcContext.termsAcceptanceRequired && !areTermsAccepted)
                                }
                            >
                                Create an account
                            </button>
                        ) : (
                            <input
                                disabled={
                                    !isFormSubmittable ||
                                    (kcContext.termsAcceptanceRequired && !areTermsAccepted)
                                }
                                className="auth-console-btn auth-console-btn-primary"
                                type="submit"
                                value="Create an account"
                            />
                        ))}
                </div>
            </div>

            <div className="auth-console-register-footer">
                <a className="auth-console-link" href={kcContext.url.loginUrl}>
                    {msg("backToLogin")}
                </a>
            </div>
        </form>
    );
}
