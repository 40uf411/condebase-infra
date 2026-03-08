import { createTheme } from "@mui/material/styles";

const darkTheme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#5f9cb7",
      dark: "#41778f",
      light: "#7bb8d2",
      contrastText: "#09161d",
    },
    secondary: {
      main: "#d0915c",
      dark: "#ac7548",
      light: "#e3ad7e",
      contrastText: "#25160d",
    },
    background: {
      default: "#141a22",
      paper: "#1f2630",
    },
    text: {
      primary: "#e6edf5",
      secondary: "#9cadbf",
    },
    success: {
      main: "#57c59c",
    },
    error: {
      main: "#ef8585",
    },
    warning: {
      main: "#d9a061",
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
          border: "1px solid rgba(160, 178, 194, 0.22)",
          boxShadow: "0 14px 34px rgba(0, 0, 0, 0.34)",
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

export default darkTheme;
