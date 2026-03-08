import type { ReactNode } from "react";
import type { ClassKey } from "@keycloakify/login-ui/useKcClsx";

type Classes = { [key in ClassKey]?: string };

type StyleLevelCustomization = {
    doUseDefaultCss: boolean;
    classes?: Classes;
    Provider?: (props: { children: ReactNode }) => ReactNode;
};

export function useStyleLevelCustomization(): StyleLevelCustomization {
    return {
        doUseDefaultCss: false,
        classes: {
            kcHtmlClass: "auth-console-html",
            kcBodyClass: "auth-console-body",
            kcFormGroupClass: "auth-console-form-group",
            kcFormClass: "auth-console-form",
            kcLabelClass: "auth-console-label",
            kcLabelWrapperClass: "auth-console-label-wrap",
            kcInputWrapperClass: "auth-console-input-wrap",
            kcInputClass: "auth-console-input",
            kcInputGroup: "auth-console-password-wrap",
            kcInputErrorMessageClass: "auth-console-field-error",
            kcInputHelperTextBeforeClass: "auth-console-helptext",
            kcInputHelperTextAfterClass: "auth-console-helptext",
            kcFormPasswordVisibilityButtonClass: "auth-console-password-toggle",
            kcFormOptionsClass: "auth-console-options-row",
            kcFormOptionsWrapperClass: "auth-console-link-wrap",
            kcFormButtonsClass: "auth-console-actions",
            kcButtonPrimaryClass: "auth-console-btn-primary",
            kcButtonDefaultClass: "auth-console-btn-secondary",
            kcButtonClass: "auth-console-btn",
            kcButtonBlockClass: "auth-console-btn-block",
            kcButtonLargeClass: "auth-console-btn-large",
            kcCheckboxInputClass: "auth-console-checkbox-input",
            kcInputClassRadio: "auth-console-choice",
            kcInputClassRadioInput: "auth-console-choice-input",
            kcInputClassRadioLabel: "auth-console-choice-label",
            kcInputClassCheckbox: "auth-console-choice",
            kcInputClassCheckboxInput: "auth-console-choice-input",
            kcInputClassCheckboxLabel: "auth-console-choice-label",
            kcInputClassRadioCheckboxLabelDisabled: "auth-console-choice-label-disabled",
            kcLocaleDropDownClass: "auth-console-locale",
            kcLocaleListClass: "auth-console-locale-list"
        }
    };
}
