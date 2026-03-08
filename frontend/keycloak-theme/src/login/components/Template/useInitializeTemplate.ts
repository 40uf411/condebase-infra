/* eslint-disable */

import { useEffect } from "react";
import { useInsertScriptTags } from "@keycloakify/login-ui/tools/useInsertScriptTags";
import { useInsertLinkTags } from "@keycloakify/login-ui/tools/useInsertLinkTags";
import { useKcClsx } from "@keycloakify/login-ui/useKcClsx";
import { useKcContext } from "../../KcContext";

export function useInitializeTemplate() {
    const { kcContext } = useKcContext();
    const { url, scripts } = kcContext;
    const resourcesCommonPath = `${url.resourcesPath}/resources-common`;

    const { doUseDefaultCss } = useKcClsx();

    const stylesheetHrefs = [
        ...(doUseDefaultCss
            ? [
                  `${resourcesCommonPath}/node_modules/@patternfly/patternfly/patternfly.min.css`,
                  `${resourcesCommonPath}/node_modules/patternfly/dist/css/patternfly.min.css`,
                  `${resourcesCommonPath}/node_modules/patternfly/dist/css/patternfly-additions.min.css`,
                  `${resourcesCommonPath}/lib/pficon/pficon.css`,
                  `${url.resourcesPath}/css/login.css`
              ]
            : []),
        `${url.resourcesPath}/dist/theme-overrides.css`
    ];

    const { areAllStyleSheetsLoaded } = useInsertLinkTags({
        effectId: "Template",
        hrefs: stylesheetHrefs
    });

    const { insertScriptTags } = useInsertScriptTags({
        effectId: "Template",
        scriptTags: [
            // NOTE: The importmap is added in by the FTL script because it's too late to add it here.
            {
                type: "module",
                src: `${url.resourcesPath}/js/menu-button-links.js`
            },
            ...(scripts === undefined
                ? []
                : scripts.map(src => ({
                      type: "text/javascript" as const,
                      src
                  }))),
            {
                type: "module",
                textContent: [
                    `import { startSessionPolling, checkAuthSession } from "${url.resourcesPath}/js/authChecker.js";`,
                    ``,
                    `startSessionPolling("${url.ssoLoginInOtherTabsUrl}");`,
                    kcContext.authenticationSession === undefined
                        ? ""
                        : `checkAuthSession("${kcContext.authenticationSession.authSessionIdHash}");`
                ].join("\n")
            }
        ]
    });

    useEffect(() => {
        if (areAllStyleSheetsLoaded) {
            insertScriptTags();
        }
    }, [areAllStyleSheetsLoaded]);

    return { isReadyToRender: areAllStyleSheetsLoaded };
}
