import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import AccountCircleRoundedIcon from "@mui/icons-material/AccountCircleRounded";
import ArrowForwardRoundedIcon from "@mui/icons-material/ArrowForwardRounded";
import HubRoundedIcon from "@mui/icons-material/HubRounded";
import InsightsRoundedIcon from "@mui/icons-material/InsightsRounded";
import FileUploadRoundedIcon from "@mui/icons-material/FileUploadRounded";
import HomeRoundedIcon from "@mui/icons-material/HomeRounded";
import LoginRoundedIcon from "@mui/icons-material/LoginRounded";
import LogoutRoundedIcon from "@mui/icons-material/LogoutRounded";
import MenuRoundedIcon from "@mui/icons-material/MenuRounded";
import PersonAddAltRoundedIcon from "@mui/icons-material/PersonAddAltRounded";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import SecurityRoundedIcon from "@mui/icons-material/SecurityRounded";
import TerminalRoundedIcon from "@mui/icons-material/TerminalRounded";
import TuneRoundedIcon from "@mui/icons-material/TuneRounded";
import VpnKeyRoundedIcon from "@mui/icons-material/VpnKeyRounded";
import {
  Alert,
  Avatar,
  Box,
  Button,
  Chip,
  CircularProgress,
  CssBaseline,
  Divider,
  FormControl,
  IconButton,
  InputAdornment,
  InputLabel,
  Menu,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  ThemeProvider,
  Tooltip,
  Typography,
  useMediaQuery,
} from "@mui/material";

import {
  buildLoginUrl,
  buildRegistrationUrl,
  fetchAuthState,
  fetchProfile,
  logout,
  startLogin,
  startRegistration,
  updateUserPreferences,
  uploadProfilePicture,
} from "./api";
import darkTheme from "./theme-dark";
import lightTheme from "./theme-light";
import {
  DEFAULT_LANGUAGE,
  getDictionary,
  LANGUAGE_LABEL_KEYS,
  normalizeLanguage,
  SUPPORTED_LANGUAGES,
  translate,
} from "./i18n";
import { useApiError } from "./hooks/useApiError";

const DEFAULT_PREFERENCES = {
  language: DEFAULT_LANGUAGE,
  theme: "light",
};

const TERMINAL_HISTORY_LIMIT = 180;

function normalizeTheme(theme) {
  if (typeof theme !== "string") {
    return "light";
  }
  const normalized = theme.trim().toLowerCase();
  return normalized === "dark" ? "dark" : "light";
}

function resolvePreferences(rawPreferences) {
  if (!rawPreferences || typeof rawPreferences !== "object") {
    return { ...DEFAULT_PREFERENCES };
  }

  return {
    language: normalizeLanguage(rawPreferences.language),
    theme: normalizeTheme(rawPreferences.theme),
  };
}

function normalizeSearchValue(value) {
  if (value === undefined || value === null) {
    return "";
  }
  return String(value).toLowerCase();
}

function includesSearch(value, search) {
  if (!search) {
    return true;
  }
  return normalizeSearchValue(value).includes(search);
}

function formatRetrySeconds(rawValue) {
  const seconds = Number(rawValue);
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return null;
  }
  return `${seconds}s`;
}

function buildCallbackErrorMessage(params, t) {
  const code = params.get("error");
  if (!code) {
    return null;
  }

  const retryAfter = formatRetrySeconds(params.get("retry_after"));
  const errorDescription = params.get("error_description");

  switch (code) {
    case "rate_limited":
      return retryAfter
        ? t("callbackErrorRateLimited", { retry: retryAfter })
        : t("callbackErrorRateLimitedNoRetry");
    case "login_temporarily_blocked":
      return retryAfter
        ? t("callbackErrorLoginBlocked", { retry: retryAfter })
        : t("callbackErrorLoginBlockedNoRetry");
    case "invalid_or_expired_state":
      return t("callbackErrorInvalidState");
    case "missing_code_or_state":
      return t("callbackErrorMissingCodeState");
    case "access_denied":
      return t("callbackErrorAccessDenied");
    default:
      if (errorDescription) {
        return `${code}: ${errorDescription}`;
      }
      return t("callbackErrorUnknown", { code });
  }
}

function createTerminalLine(message, level = "info") {
  return {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    timestamp: new Date(),
    message,
    level,
  };
}

function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const compactViewport = useMediaQuery("(max-width: 1100px)");

  const [authState, setAuthState] = useState({
    loading: true,
    authenticated: false,
    user: null,
    csrfToken: null,
    error: null,
  });
  const [preferences, setPreferences] = useState(DEFAULT_PREFERENCES);
  const [savingPreferences, setSavingPreferences] = useState(false);
  const [preferenceMessage, setPreferenceMessage] = useState(null);
  const [logoutError, setLogoutError] = useState(null);
  const [loggingOut, setLoggingOut] = useState(false);
  const [navExpanded, setNavExpanded] = useState(true);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [terminalOpen, setTerminalOpen] = useState(false);
  const [terminalLines, setTerminalLines] = useState([createTerminalLine("console ready")]);
  const [statusTime, setStatusTime] = useState(() => new Date());
  const [profileMenuAnchor, setProfileMenuAnchor] = useState(null);

  const dictionary = useMemo(() => getDictionary(preferences.language), [preferences.language]);
  const { getErrorMessage } = useApiError();
  const t = useCallback((key, params) => translate(dictionary, key, params), [dictionary]);
  const callbackErrorMessage = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return buildCallbackErrorMessage(params, t);
  }, [location.search, t]);
  const muiTheme = useMemo(() => (preferences.theme === "dark" ? darkTheme : lightTheme), [preferences.theme]);
  const profileMenuOpen = Boolean(profileMenuAnchor);
  const currentPath = location.pathname;
  const searchableQuery = searchQuery.trim().toLowerCase();
  const loginUrl = useMemo(() => buildLoginUrl("/home", true), []);
  const registrationUrl = useMemo(() => buildRegistrationUrl("/home"), []);

  const appendTerminalLine = useCallback((message, level = "info") => {
    setTerminalLines((previous) => {
      const next = [...previous, createTerminalLine(message, level)];
      return next.slice(-TERMINAL_HISTORY_LIMIT);
    });
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", preferences.theme);
  }, [preferences.theme]);

  useEffect(() => {
    const timer = setInterval(() => setStatusTime(new Date()), 30000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!compactViewport) {
      setMobileNavOpen(false);
    }
  }, [compactViewport]);

  const refreshAuthState = useCallback(async () => {
    setAuthState((previous) => ({ ...previous, loading: true, error: null }));
    try {
      const response = await fetchAuthState();
      const user = response?.user || null;
      setAuthState({
        loading: false,
        authenticated: Boolean(response?.authenticated),
        user,
        csrfToken: response?.csrfToken || null,
        error: null,
      });
      setPreferences(resolvePreferences(user?.preferences));
      appendTerminalLine(response?.authenticated ? t("terminalSessionActive") : t("terminalSessionGuest"));
    } catch (error) {
      setAuthState({
        loading: false,
        authenticated: false,
        user: null,
        csrfToken: null,
        error: getErrorMessage(error, t("sessionFetchFailed")),
      });
      setPreferences({ ...DEFAULT_PREFERENCES });
      appendTerminalLine(t("terminalSessionFailed"), "error");
    }
  }, [appendTerminalLine, t]);

  useEffect(() => {
    void refreshAuthState();
  }, [refreshAuthState]);

  const onLogin = useCallback(() => {
    appendTerminalLine(t("terminalLoginRedirect"));
    startLogin("/home", true);
  }, [appendTerminalLine, t]);

  const onRegister = useCallback(() => {
    appendTerminalLine(t("terminalRegistrationRedirect"));
    startRegistration("/home");
  }, [appendTerminalLine, t]);

  const onLogout = useCallback(async () => {
    setLoggingOut(true);
    setLogoutError(null);
    try {
      const response = await logout(authState.csrfToken);
      setAuthState({
        loading: false,
        authenticated: false,
        user: null,
        csrfToken: null,
        error: null,
      });
      setPreferences({ ...DEFAULT_PREFERENCES });
      appendTerminalLine(t("terminalLogoutComplete"), "success");
      if (response?.logoutUrl) {
        window.location.assign(response.logoutUrl);
        return;
      }
      navigate("/", { replace: true });
    } catch (error) {
      setLogoutError(getErrorMessage(error, t("logoutFailed")));
      appendTerminalLine(t("terminalLogoutFailed"), "error");
    } finally {
      setLoggingOut(false);
    }
  }, [authState.csrfToken, appendTerminalLine, navigate, t]);

  const onSavePreferences = useCallback(
    async (nextPreferences, options = {}) => {
      const { silent = false } = options;
      const next = resolvePreferences(nextPreferences);

      if (next.language === preferences.language && next.theme === preferences.theme) {
        return;
      }

      setPreferenceMessage(null);
      setPreferences(next);

      if (!authState.authenticated) {
        if (!silent) {
          setPreferenceMessage({ type: "success", key: "savePreferencesLocal" });
        }
        return;
      }

      setSavingPreferences(true);
      try {
        const response = await updateUserPreferences(next, authState.csrfToken);
        const resolved = resolvePreferences(response?.preferences ?? response?.user?.preferences ?? next);
        setPreferences(resolved);
        if (response?.user) {
          setAuthState((old) => ({
            ...old,
            user: response.user,
          }));
        }
        if (!silent) {
          setPreferenceMessage({ type: "success", key: "savePreferencesSuccess" });
        }
        appendTerminalLine(t("terminalPreferencesSynced"), "success");
      } catch (error) {
        setPreferenceMessage({
          type: "error",
          text: getErrorMessage(error, t("savePreferencesError")),
        });
        appendTerminalLine(t("savePreferencesError"), "error");
      } finally {
        setSavingPreferences(false);
      }
    },
    [authState.authenticated, authState.csrfToken, appendTerminalLine, getErrorMessage, preferences, t]
  );

  const preferenceAlert = useMemo(() => {
    if (!preferenceMessage) {
      return null;
    }
    if (preferenceMessage.text) {
      return preferenceMessage.text;
    }
    return t(preferenceMessage.key);
  }, [preferenceMessage, t]);

  const onToggleNavigation = useCallback(() => {
    if (compactViewport) {
      setMobileNavOpen((previous) => !previous);
      return;
    }
    setNavExpanded((previous) => !previous);
  }, [compactViewport]);

  const onNavigate = useCallback(
    (path) => {
      navigate(path);
      if (compactViewport) {
        setMobileNavOpen(false);
      }
    },
    [compactViewport, navigate]
  );

  const activeUserName = authState.user?.name || authState.user?.email || authState.user?.username || t("unknownUser");

  const rootClasses = [
    "app-layout",
    navExpanded ? "nav-expanded" : "nav-collapsed",
    detailsOpen ? "details-open" : "details-closed",
    terminalOpen ? "with-terminal" : "",
    mobileNavOpen ? "mobile-nav-open" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const showIntroPage = !authState.loading && !authState.authenticated && currentPath === "/";

  if (showIntroPage) {
    return (
      <ThemeProvider theme={muiTheme}>
        <CssBaseline />
        <IntroPage callbackErrorMessage={callbackErrorMessage} loginUrl={loginUrl} registrationUrl={registrationUrl} t={t} />
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider theme={muiTheme}>
      <CssBaseline />
      <Box className={rootClasses}>
        <Box className="ambient-shape ambient-shape-a" />
        <Box className="ambient-shape ambient-shape-b" />
        <Box className="ambient-shape ambient-shape-c" />

        <header className="top-panel">
          <Box className="top-panel-left">
            <Tooltip title={t("navToggleMenu")}>
              <IconButton color="inherit" className="top-icon-button" onClick={onToggleNavigation}>
                <MenuRoundedIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title={detailsOpen ? t("hideDetailsPanel") : t("showDetailsPanel")}>
              <IconButton color="inherit" className="top-icon-button" onClick={() => setDetailsOpen((p) => !p)}>
                <TuneRoundedIcon />
              </IconButton>
            </Tooltip>
            <TextField
              className="top-search"
              size="small"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder={t("searchPlaceholder")}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchRoundedIcon fontSize="small" />
                  </InputAdornment>
                ),
              }}
            />
          </Box>
          <Box className="top-panel-right">
            <Chip
              icon={<AccountCircleRoundedIcon />}
              color={authState.authenticated ? "success" : "default"}
              variant={authState.authenticated ? "filled" : "outlined"}
              label={authState.authenticated ? t("statusAuthenticated") : t("statusSignedOut")}
            />
            <Tooltip title={activeUserName}>
              <IconButton color="inherit" className="avatar-button" onClick={(event) => setProfileMenuAnchor(event.currentTarget)}>
                <Avatar src={authState.user?.picture || undefined} className="top-avatar">
                  {activeUserName.charAt(0).toUpperCase()}
                </Avatar>
              </IconButton>
            </Tooltip>
          </Box>
        </header>

        <Box className="workspace-shell">
          <aside className="left-nav-panel">
            <Box className="nav-heading">
              <Typography variant="overline" className="nav-heading-text">
                {t("appTitle")}
              </Typography>
            </Box>
            <Stack spacing={1} className="nav-stack">
              <NavButton
                compact={!navExpanded && !compactViewport}
                active={currentPath === "/home"}
                icon={<HomeRoundedIcon fontSize="small" />}
                label={t("navHome")}
                onClick={() => onNavigate("/home")}
              />
              <NavButton
                compact={!navExpanded && !compactViewport}
                active={currentPath === "/profile"}
                icon={<VpnKeyRoundedIcon fontSize="small" />}
                label={t("navProfile")}
                onClick={() => onNavigate("/profile")}
              />
              {!authState.authenticated ? (
                <>
                  <NavButton
                    compact={!navExpanded && !compactViewport}
                    icon={<LoginRoundedIcon fontSize="small" />}
                    label={t("navLogin")}
                    onClick={onLogin}
                  />
                  <NavButton
                    compact={!navExpanded && !compactViewport}
                    icon={<PersonAddAltRoundedIcon fontSize="small" />}
                    label={t("navRegister")}
                    onClick={onRegister}
                  />
                </>
              ) : (
                <NavButton
                  compact={!navExpanded && !compactViewport}
                  icon={<LogoutRoundedIcon fontSize="small" />}
                  label={loggingOut ? t("actionSigningOut") : t("actionLogout")}
                  onClick={() => void onLogout()}
                />
              )}
            </Stack>
            <Box className="nav-footer">
              <Button variant="text" size="small" onClick={() => void refreshAuthState()} disabled={authState.loading}>
                {t("actionRefreshSession")}
              </Button>
            </Box>
          </aside>

          {compactViewport ? <Box className="mobile-nav-overlay" onClick={() => setMobileNavOpen(false)} /> : null}

          <aside className="left-detail-panel">
            <DetailsPanel
              authenticated={authState.authenticated}
              user={authState.user}
              preferences={preferences}
              savingPreferences={savingPreferences}
              onSavePreferences={onSavePreferences}
              onLogin={onLogin}
              onRegister={onRegister}
              t={t}
              searchQuery={searchQuery}
            />
          </aside>

          <main className="main-stage">
            <Paper elevation={0} className="title-panel">
              <Stack spacing={0.75}>
                <Typography variant="h4" className="title-text">
                  {t("appTitle")}
                </Typography>
                <Typography color="text.secondary">{t("appSubtitle")}</Typography>
              </Stack>
            </Paper>

            {logoutError ? <Alert severity="error">{logoutError}</Alert> : null}
            {authState.error ? <Alert severity="error">{authState.error}</Alert> : null}
            {preferenceAlert ? <Alert severity={preferenceMessage.type}>{preferenceAlert}</Alert> : null}

            {authState.loading ? (
              <LoadingPanel t={t} />
            ) : (
              <Routes>
                <Route
                  path="/"
                  element={<Navigate to="/home" replace />}
                />
                <Route
                  path="/home"
                  element={
                    <LandingPage
                      authenticated={authState.authenticated}
                      user={authState.user}
                      callbackErrorMessage={callbackErrorMessage}
                      onLogin={onLogin}
                      onRegister={onRegister}
                      onGoProfile={() => onNavigate("/profile")}
                      t={t}
                      searchQuery={searchableQuery}
                    />
                  }
                />
                <Route
                  path="/profile"
                  element={
                    <ProfilePage
                      authenticated={authState.authenticated}
                      csrfToken={authState.csrfToken}
                      onLogin={onLogin}
                      onRegister={onRegister}
                      onLogout={onLogout}
                      onSessionRefresh={refreshAuthState}
                      loggingOut={loggingOut}
                      t={t}
                      searchQuery={searchableQuery}
                      onTerminalLine={appendTerminalLine}
                    />
                  }
                />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            )}
          </main>
        </Box>

        {terminalOpen ? (
          <TerminalPanel
            lines={terminalLines}
            t={t}
            onClear={() => setTerminalLines([createTerminalLine("console cleared")])}
          />
        ) : null}

        <footer className="status-bar">
          <Box className="status-left">
            <StatusPill label={t("statusAuth")} value={authState.authenticated ? t("statusAuthenticated") : t("statusGuest")} />
            <StatusPill label={t("statusLanguage")} value={preferences.language.toUpperCase()} />
            <StatusPill label={t("statusTheme")} value={preferences.theme === "dark" ? t("themeDark") : t("themeLight")} />
            <StatusPill label={t("statusRoute")} value={currentPath} />
            <StatusPill
              label={t("statusTime")}
              value={statusTime.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            />
          </Box>
          <Button
            size="small"
            color="inherit"
            startIcon={<TerminalRoundedIcon />}
            onClick={() => setTerminalOpen((previous) => !previous)}
          >
            {terminalOpen ? t("terminalHide") : t("terminalShow")}
          </Button>
        </footer>

        <Menu anchorEl={profileMenuAnchor} open={profileMenuOpen} onClose={() => setProfileMenuAnchor(null)}>
          <MenuItem
            onClick={() => {
              setProfileMenuAnchor(null);
              onNavigate("/profile");
            }}
          >
            {t("menuOpenProfile")}
          </MenuItem>
          <MenuItem
            onClick={() => {
              setProfileMenuAnchor(null);
              void onSavePreferences(
                {
                  ...preferences,
                  theme: preferences.theme === "dark" ? "light" : "dark",
                },
                { silent: true }
              );
            }}
          >
            {t("menuToggleTheme")}
          </MenuItem>
          <Divider />
          {SUPPORTED_LANGUAGES.map((languageCode) => (
            <MenuItem
              key={languageCode}
              selected={preferences.language === languageCode}
              onClick={() => {
                setProfileMenuAnchor(null);
                void onSavePreferences(
                  {
                    ...preferences,
                    language: languageCode,
                  },
                  { silent: true }
                );
              }}
            >
              {t("menuLanguageOption", { language: t(LANGUAGE_LABEL_KEYS[languageCode]) })}
            </MenuItem>
          ))}
          <Divider />
          {authState.authenticated ? (
            <MenuItem
              onClick={() => {
                setProfileMenuAnchor(null);
                void onLogout();
              }}
            >
              {t("actionLogout")}
            </MenuItem>
          ) : (
            <>
              <MenuItem
                onClick={() => {
                  setProfileMenuAnchor(null);
                  onLogin();
                }}
              >
                {t("actionLogin")}
              </MenuItem>
              <MenuItem
                onClick={() => {
                  setProfileMenuAnchor(null);
                  onRegister();
                }}
              >
                {t("actionCreateAccount")}
              </MenuItem>
            </>
          )}
        </Menu>
      </Box>
    </ThemeProvider>
  );
}

function NavButton({ icon, label, onClick, active = false, compact = false }) {
  return (
    <Tooltip title={compact ? label : ""} placement="right">
      <Button
        variant={active ? "contained" : "text"}
        color={active ? "primary" : "inherit"}
        onClick={onClick}
        className={`nav-button ${compact ? "compact" : "expanded"}`}
        startIcon={icon}
      >
        {compact ? "" : label}
      </Button>
    </Tooltip>
  );
}

function LoadingPanel({ t }) {
  return (
    <Paper elevation={0} className="surface-panel loading-panel">
      <Stack spacing={1.5} alignItems="center">
        <CircularProgress size={28} />
        <Typography variant="body1">{t("loadingSession")}</Typography>
      </Stack>
    </Paper>
  );
}

function DetailsPanel({
  authenticated,
  user,
  preferences,
  savingPreferences,
  onSavePreferences,
  onLogin,
  onRegister,
  t,
  searchQuery,
}) {
  const displayName = user?.name || user?.email || user?.username || t("unknownUser");

  return (
    <Stack spacing={1.5} className="details-content">
      <Paper elevation={0} className="detail-card">
        <Stack spacing={1}>
          <Typography variant="overline">{t("detailsPanelTitle")}</Typography>
          <Typography variant="body2" color="text.secondary">
            {t("detailsPanelSubtitle")}
          </Typography>
        </Stack>
      </Paper>

      <Paper elevation={0} className="detail-card">
        <Stack spacing={1.5}>
          <Typography variant="subtitle2">{t("detailsProfile")}</Typography>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <Avatar src={user?.picture || undefined} className="details-avatar">
              {displayName.charAt(0).toUpperCase()}
            </Avatar>
            <Box>
              <Typography variant="body2">{displayName}</Typography>
              <Typography variant="caption" color="text.secondary">
                {authenticated ? t("statusAuthenticated") : t("statusSignedOut")}
              </Typography>
            </Box>
          </Stack>
          {!authenticated ? (
            <Stack direction="row" spacing={1}>
              <Button size="small" variant="contained" onClick={onLogin}>
                {t("actionLogin")}
              </Button>
              <Button size="small" variant="outlined" onClick={onRegister}>
                {t("actionCreateAccount")}
              </Button>
            </Stack>
          ) : null}
        </Stack>
      </Paper>

      <Paper elevation={0} className="detail-card">
        <Stack spacing={1.25}>
          <Typography variant="subtitle2">{t("detailsConfig")}</Typography>
          <FormControl size="small" fullWidth>
            <InputLabel id="left-language-select-label">{t("languageLabel")}</InputLabel>
            <Select
              labelId="left-language-select-label"
              value={preferences.language}
              label={t("languageLabel")}
              disabled={savingPreferences}
              onChange={(event) => {
                void onSavePreferences(
                  {
                    ...preferences,
                    language: event.target.value,
                  },
                  { silent: true }
                );
              }}
            >
              {SUPPORTED_LANGUAGES.map((languageCode) => (
                <MenuItem key={languageCode} value={languageCode}>
                  {t(LANGUAGE_LABEL_KEYS[languageCode])}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" fullWidth>
            <InputLabel id="left-theme-select-label">{t("themeLabel")}</InputLabel>
            <Select
              labelId="left-theme-select-label"
              value={preferences.theme}
              label={t("themeLabel")}
              disabled={savingPreferences}
              onChange={(event) => {
                void onSavePreferences(
                  {
                    ...preferences,
                    theme: event.target.value,
                  },
                  { silent: true }
                );
              }}
            >
              <MenuItem value="light">{t("themeLight")}</MenuItem>
              <MenuItem value="dark">{t("themeDark")}</MenuItem>
            </Select>
          </FormControl>
          <Typography variant="caption" color="text.secondary">
            {savingPreferences ? t("actionSavingPreferences") : t("savePreferencesHint")}
          </Typography>
        </Stack>
      </Paper>

      <Paper elevation={0} className="detail-card">
        <Typography variant="subtitle2" gutterBottom>
          {t("detailsSearch")}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {searchQuery ? searchQuery : t("detailsSearchEmpty")}
        </Typography>
      </Paper>
    </Stack>
  );
}

function IntroPage({ callbackErrorMessage, loginUrl, registrationUrl, t }) {
  const introFeatures = [
    {
      icon: <HubRoundedIcon fontSize="small" />,
      title: t("introFeatureIdentityTitle"),
      body: t("introFeatureIdentityBody"),
    },
    {
      icon: <SecurityRoundedIcon fontSize="small" />,
      title: t("introFeatureSecurityTitle"),
      body: t("introFeatureSecurityBody"),
    },
    {
      icon: <InsightsRoundedIcon fontSize="small" />,
      title: t("introFeatureVisibilityTitle"),
      body: t("introFeatureVisibilityBody"),
    },
  ];

  return (
    <Box className="intro-page">
      <Box className="intro-grid-overlay" />
      <Box className="intro-glow intro-glow-a" />
      <Box className="intro-glow intro-glow-b" />

      <header className="intro-nav">
        <Stack direction="row" spacing={1.2} alignItems="center">
          <Avatar className="intro-brand-icon">K</Avatar>
          <Typography variant="subtitle1" className="intro-brand-text">
            {t("introBrand")}
          </Typography>
        </Stack>
        <Stack className="intro-nav-links" direction="row" spacing={2}>
          <Typography variant="body2">{t("introNavPlatform")}</Typography>
          <Typography variant="body2">{t("introNavSecurity")}</Typography>
          <Typography variant="body2">{t("introNavDevelopers")}</Typography>
        </Stack>
        <Stack direction="row" spacing={1}>
          <Button component="a" href={loginUrl} variant="text" color="inherit">
            {t("promoActionLogin")}
          </Button>
          <Button component="a" href={registrationUrl} variant="contained" endIcon={<ArrowForwardRoundedIcon />}>
            {t("promoActionRegister")}
          </Button>
        </Stack>
      </header>

      <main className="intro-main">
        {callbackErrorMessage ? (
          <Alert severity="warning">
            {t("callbackErrorPrefix")} <strong>{callbackErrorMessage}</strong>
          </Alert>
        ) : null}

        <section className="intro-hero">
          <Box className="intro-hero-copy">
            <Typography variant="overline" className="intro-eyebrow">
              {t("introEyebrow")}
            </Typography>
            <Typography variant="h2" className="intro-title">
              {t("introTitle")}
            </Typography>
            <Typography variant="h6" color="text.secondary" className="intro-subtitle">
              {t("introSubtitle")}
            </Typography>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.2}>
              <Button component="a" href={loginUrl} variant="contained" size="large">
                {t("promoActionLogin")}
              </Button>
              <Button component="a" href={registrationUrl} variant="outlined" size="large">
                {t("promoActionRegister")}
              </Button>
            </Stack>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={3} className="intro-stats">
              <Box>
                <Typography variant="h5">99.95%</Typography>
                <Typography variant="body2" color="text.secondary">
                  {t("introStatAvailability")}
                </Typography>
              </Box>
              <Box>
                <Typography variant="h5">OIDC + SAML</Typography>
                <Typography variant="body2" color="text.secondary">
                  {t("introStatStandards")}
                </Typography>
              </Box>
              <Box>
                <Typography variant="h5">{t("introStatInstantLabel")}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {t("introStatInstantValue")}
                </Typography>
              </Box>
            </Stack>
          </Box>

          <Paper elevation={0} className="intro-console">
            <Box className="intro-console-head">
              <span />
              <span />
              <span />
            </Box>
            <Box className="intro-console-body">
              <Typography component="pre">
                {`POST /api/auth/login\n-> realm: production\n-> provider: keycloak\n\nGET /api/profile\n-> claims: 27\n-> access_token: active\n\nPUT /api/profile/preferences\n-> language: en\n-> theme: dark`}
              </Typography>
            </Box>
          </Paper>
        </section>

        <section className="intro-feature-grid">
          {introFeatures.map((feature) => (
            <Paper key={feature.title} elevation={0} className="intro-feature-card">
              <Box className="intro-feature-icon">{feature.icon}</Box>
              <Typography variant="h6">{feature.title}</Typography>
              <Typography variant="body2" color="text.secondary">
                {feature.body}
              </Typography>
            </Paper>
          ))}
        </section>

        <section className="intro-final-cta">
          <Typography variant="h5">{t("introFinalTitle")}</Typography>
          <Typography variant="body1" color="text.secondary">
            {t("introFinalBody")}
          </Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.2}>
            <Button component="a" href={registrationUrl} variant="contained">
              {t("promoActionRegister")}
            </Button>
            <Button component="a" href={loginUrl} variant="text">
              {t("promoActionLogin")}
            </Button>
          </Stack>
        </section>
      </main>
    </Box>
  );
}

function LandingPage({ authenticated, user, callbackErrorMessage, onLogin, onRegister, onGoProfile, t, searchQuery }) {
  const displayName = user?.name || user?.email || t("unknownUser");
  const cards = [
    {
      id: "auth",
      title: authenticated ? t("landingAuthTitle", { name: displayName }) : t("landingGuestTitle"),
      body: authenticated ? t("landingAuthBody") : t("landingGuestBody"),
    },
    {
      id: "prefs",
      title: t("preferencesTitle"),
      body: t("savePreferencesHint"),
    },
    {
      id: "tokens",
      title: t("tokenDetails"),
      body: t("tokenPayload"),
    },
  ];

  const visibleCards = cards.filter(
    (card) => includesSearch(card.title, searchQuery) || includesSearch(card.body, searchQuery)
  );

  return (
    <Stack spacing={2}>
      {callbackErrorMessage ? (
        <Alert severity="warning">
          {t("callbackErrorPrefix")} <strong>{callbackErrorMessage}</strong>
        </Alert>
      ) : null}

      <Paper elevation={0} className="surface-panel">
        <Stack spacing={2}>
          <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={2}>
            <Box>
              <Typography variant="h5">
                {authenticated ? t("landingAuthTitle", { name: displayName }) : t("landingGuestTitle")}
              </Typography>
              <Typography color="text.secondary">
                {authenticated ? t("landingAuthBody") : t("landingGuestBody")}
              </Typography>
            </Box>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
              {!authenticated ? (
                <>
                  <Button variant="contained" startIcon={<LoginRoundedIcon />} onClick={onLogin}>
                    {t("actionLogin")}
                  </Button>
                  <Button variant="outlined" startIcon={<PersonAddAltRoundedIcon />} onClick={onRegister}>
                    {t("actionCreateAccount")}
                  </Button>
                </>
              ) : (
                <Button variant="contained" startIcon={<VpnKeyRoundedIcon />} onClick={onGoProfile}>
                  {t("actionViewProfile")}
                </Button>
              )}
            </Stack>
          </Stack>
        </Stack>
      </Paper>

      <Box className="dashboard-grid">
        {visibleCards.map((card) => (
          <Paper key={card.id} elevation={0} className="surface-panel">
            <Typography variant="subtitle1" gutterBottom>
              {card.title}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {card.body}
            </Typography>
          </Paper>
        ))}
      </Box>

      {!visibleCards.length ? <Alert severity="info">{t("searchNoResults")}</Alert> : null}
    </Stack>
  );
}

function ProfilePage({
  authenticated,
  csrfToken,
  onLogin,
  onRegister,
  onLogout,
  onSessionRefresh,
  loggingOut,
  t,
  searchQuery,
  onTerminalLine,
}) {
  const { getErrorMessage } = useApiError();
  const [loading, setLoading] = useState(authenticated);
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState(null);
  const [uploadingPicture, setUploadingPicture] = useState(false);
  const [pictureMessage, setPictureMessage] = useState(null);
  const fileInputRef = useRef(null);
  useEffect(() => {
    let active = true;

    if (!authenticated) {
      setLoading(false);
      setProfile(null);
      setError(null);
      setPictureMessage(null);
      return () => {
        active = false;
      };
    }

    setLoading(true);
    setError(null);
    fetchProfile()
      .then((response) => {
        if (!active) {
          return;
        }
        setProfile(response?.user || null);
        setLoading(false);
        onTerminalLine(t("profileOverview"), "success");
      })
      .catch((requestError) => {
        if (!active) {
          return;
        }
        setError(getErrorMessage(requestError, t("profileLoadFailed")));
        setLoading(false);
        onTerminalLine(t("profileLoadFailed"), "error");
        if (requestError?.status === 401) {
          void onSessionRefresh();
        }
      });

    return () => {
      active = false;
    };
  }, [authenticated, onSessionRefresh, onTerminalLine, t]);

  const onChoosePicture = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const onPictureSelected = useCallback(
    async (event) => {
      const selected = event.target.files?.[0];
      event.target.value = "";

      if (!selected) {
        return;
      }

      setPictureMessage(null);
      setUploadingPicture(true);

      try {
        const response = await uploadProfilePicture(selected, csrfToken);
        if (response?.user) {
          setProfile(response.user);
        } else if (response?.picture) {
          setProfile((previousProfile) =>
            previousProfile ? { ...previousProfile, picture: response.picture } : previousProfile
          );
        }
        setPictureMessage({
          type: "success",
          key: "profilePictureUpdated",
        });
        onTerminalLine(t("profilePictureUpdated"), "success");
        void onSessionRefresh();
      } catch (uploadError) {
        setPictureMessage({
          type: "error",
          text: getErrorMessage(uploadError, t("profilePictureUploadFailed")),
        });
        onTerminalLine(t("profilePictureUploadFailed"), "error");
      } finally {
        setUploadingPicture(false);
      }
    },
    [csrfToken, getErrorMessage, onSessionRefresh, onTerminalLine, t]
  );

  if (!authenticated) {
    return (
      <Paper elevation={0} className="surface-panel">
        <Stack spacing={2}>
          <Typography variant="h5">{t("notSignedInTitle")}</Typography>
          <Typography color="text.secondary">{t("notSignedInBody")}</Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
            <Button variant="contained" startIcon={<LoginRoundedIcon />} onClick={onLogin}>
              {t("actionLogin")}
            </Button>
            <Button variant="outlined" startIcon={<PersonAddAltRoundedIcon />} onClick={onRegister}>
              {t("actionCreateAccount")}
            </Button>
          </Stack>
        </Stack>
      </Paper>
    );
  }

  if (loading) {
    return <LoadingPanel t={t} />;
  }

  const search = searchQuery.trim().toLowerCase();
  const profileEntries = [
    { label: t("fieldName"), value: profile?.name || "-" },
    { label: t("fieldEmail"), value: profile?.email || "-" },
    { label: t("fieldUsername"), value: profile?.username || "-" },
    { label: t("fieldSub"), value: profile?.sub || "-" },
    { label: t("fieldEmailVerified"), value: String(Boolean(profile?.emailVerified)) },
    { label: t("fieldSessionIssuedAt"), value: profile?.sessionIssuedAt || "-" },
    {
      label: t("fieldRoles"),
      value: Array.isArray(profile?.roles) && profile.roles.length ? profile.roles.join(", ") : "-",
    },
    {
      label: t("fieldPermissions"),
      value: Array.isArray(profile?.permissions) && profile.permissions.length ? profile.permissions.join(", ") : "-",
    },
  ];
  const visibleProfileEntries = profileEntries.filter(
    (entry) => includesSearch(entry.label, search) || includesSearch(entry.value, search)
  );

  const accessTokenText = profile?.accessToken || t("tokenNotAvailable");
  const idTokenText = profile?.idToken || t("tokenNotAvailable");
  const tokenPayloadText = JSON.stringify(profile?.tokenResponse || {}, null, 2);
  const claimsText = JSON.stringify(profile?.claims || {}, null, 2);
  const fullPayloadText = JSON.stringify(profile || {}, null, 2);

  const showAccessToken = includesSearch(accessTokenText, search) || includesSearch(t("accessToken"), search);
  const showIdToken = includesSearch(idTokenText, search) || includesSearch(t("idToken"), search);
  const showTokenPayload = includesSearch(tokenPayloadText, search) || includesSearch(t("tokenPayload"), search);
  const showClaims = includesSearch(claimsText, search) || includesSearch(t("allClaims"), search);
  const showFullPayload = includesSearch(fullPayloadText, search) || includesSearch(t("fullPayload"), search);

  const anythingVisible =
    !search ||
    visibleProfileEntries.length > 0 ||
    showAccessToken ||
    showIdToken ||
    showTokenPayload ||
    showClaims ||
    showFullPayload;

  return (
    <Stack spacing={2.25}>
      {error ? <Alert severity="error">{error}</Alert> : null}

      <Paper elevation={0} className="surface-panel">
        <Stack spacing={2}>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2} justifyContent="space-between">
            <Typography variant="h5">{t("profileOverview")}</Typography>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
              <Button variant="outlined" onClick={() => void onSessionRefresh()}>
                {t("actionRefreshSession")}
              </Button>
              <Button variant="contained" color="secondary" disabled={loggingOut} onClick={() => void onLogout()}>
                {loggingOut ? t("actionSigningOut") : t("actionLogout")}
              </Button>
            </Stack>
          </Stack>

          {!profile ? (
            <Alert severity="warning">{t("noProfilePayload")}</Alert>
          ) : (
            <>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <Avatar src={profile.picture || undefined} alt={profile.name || profile.username || "profile"} className="profile-avatar">
                  {(profile.name || profile.username || "?").charAt(0).toUpperCase()}
                </Avatar>
                <Stack spacing={0.75}>
                  <Typography variant="subtitle1">{t("profilePictureTitle")}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {t("profilePictureHelp")}
                  </Typography>
                  <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                    <Button
                      variant="outlined"
                      startIcon={<FileUploadRoundedIcon />}
                      onClick={onChoosePicture}
                      disabled={uploadingPicture}
                    >
                      {uploadingPicture ? t("actionUploading") : t("actionUploadPicture")}
                    </Button>
                    {profile.picture ? (
                      <Button variant="text" href={profile.picture} target="_blank" rel="noreferrer">
                        {t("actionOpenImage")}
                      </Button>
                    ) : null}
                  </Stack>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/png,image/jpeg,image/gif,image/webp"
                    hidden
                    onChange={(event) => {
                      void onPictureSelected(event);
                    }}
                  />
                </Stack>
              </Stack>

              {pictureMessage ? (
                <Alert severity={pictureMessage.type}>
                  {pictureMessage.text ? pictureMessage.text : t(pictureMessage.key)}
                </Alert>
              ) : null}

              <Box className="profile-grid">
                {visibleProfileEntries.map((entry) => (
                  <ProfileField key={entry.label} label={entry.label} value={entry.value} />
                ))}
              </Box>
            </>
          )}
        </Stack>
      </Paper>

      {showAccessToken ? <CodePanel title={t("accessToken")} value={accessTokenText} /> : null}
      {showIdToken ? <CodePanel title={t("idToken")} value={idTokenText} /> : null}
      {showTokenPayload ? <CodePanel title={t("tokenPayload")} value={tokenPayloadText} /> : null}
      {showClaims ? <CodePanel title={t("allClaims")} value={claimsText} /> : null}
      {showFullPayload ? <CodePanel title={t("fullPayload")} value={fullPayloadText} /> : null}

      {!anythingVisible ? <Alert severity="info">{t("searchNoResults")}</Alert> : null}
    </Stack>
  );
}

function ProfileField({ label, value }) {
  return (
    <Paper elevation={0} className="profile-field">
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body2" className="profile-field-value">
        {value || "-"}
      </Typography>
    </Paper>
  );
}

function CodePanel({ title, value }) {
  return (
    <Paper elevation={0} className="surface-panel">
      <Stack spacing={1.25}>
        <Typography variant="h6">{title}</Typography>
        <Box component="pre" className="code-block">
          {value}
        </Box>
      </Stack>
    </Paper>
  );
}

function TerminalPanel({ lines, t, onClear }) {
  return (
    <section className="terminal-panel">
      <Box className="terminal-toolbar">
        <Typography variant="subtitle2">{t("terminalTitle")}</Typography>
        <Button size="small" onClick={onClear}>
          {t("terminalClear")}
        </Button>
      </Box>
      <Box className="terminal-body">
        {lines.map((line) => (
          <Box key={line.id} className={`terminal-line ${line.level}`}>
            <span className="terminal-time">
              {line.timestamp.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })}
            </span>
            <span className="terminal-message">{line.message}</span>
          </Box>
        ))}
      </Box>
    </section>
  );
}

function StatusPill({ label, value }) {
  return (
    <Box className="status-pill">
      <Typography component="span" className="status-pill-label">
        {label}
      </Typography>
      <Typography component="span" className="status-pill-value">
        {value}
      </Typography>
    </Box>
  );
}

export default App;
