import { createTheme } from "@mui/material/styles";

const lightTheme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#2f6379",
      dark: "#214757",
      light: "#4c859f",
      contrastText: "#f7f9fb",
    },
    secondary: {
      main: "#b86b2d",
      dark: "#8d5120",
      light: "#cf8a4e",
      contrastText: "#fdf8f2",
    },
    background: {
      default: "#f4f0e8",
      paper: "#fffdf9",
    },
    text: {
      primary: "#1d232b",
      secondary: "#5e6a78",
    },
    success: {
      main: "#2f8f68",
    },
    error: {
      main: "#ba4343",
    },
    warning: {
      main: "#b06a2c",
    },
  },
  shape: {
    borderRadius: 14,
  },
  typography: {
    fontFamily: '"Manrope", "Segoe UI", "Trebuchet MS", sans-serif',
    h1: {
      fontWeight: 700,
      letterSpacing: "-0.04em",
    },
    h2: {
      fontWeight: 700,
      letterSpacing: "-0.03em",
    },
    h3: {
      fontWeight: 700,
      letterSpacing: "-0.02em",
    },
    button: {
      textTransform: "none",
      fontWeight: 600,
      letterSpacing: "0.01em",
    },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          border: "1px solid rgba(31, 39, 49, 0.12)",
          boxShadow: "0 12px 30px rgba(20, 26, 34, 0.1)",
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          paddingLeft: 16,
          paddingRight: 16,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          fontWeight: 600,
        },
      },
    },
  },
});

export default lightTheme;
