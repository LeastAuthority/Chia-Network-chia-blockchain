import {
  makeStyles,
  Typography,
  Paper,
  Grid,
  List,
  Button,
  Box,
} from '@material-ui/core';

export const useStyles = makeStyles((theme) => ({
  walletContainer: {
    marginBottom: theme.spacing(5),
  },
  root: {
    display: 'flex',
    paddingLeft: '0px',
    color: '#000000',
  },
  appBarSpacer: theme.mixins.toolbar,
  content: {
    flexGrow: 1,
    height: '100vh',
    overflow: 'auto',
  },
  container: {
    paddingTop: theme.spacing(0),
    paddingBottom: theme.spacing(0),
    paddingRight: theme.spacing(0),
  },
  paper: {
    marginTop: theme.spacing(2),
    padding: theme.spacing(2),
    display: 'flex',
    overflow: 'auto',
    flexDirection: 'column',
    minWidth: '100%',
  },
  cardTitle: {
    paddingLeft: theme.spacing(1),
    paddingTop: theme.spacing(1),
    marginBottom: theme.spacing(1),
  },
  title: {
    paddingTop: 6,
  },
  sendButton: {
    marginTop: theme.spacing(2),
    marginBottom: theme.spacing(2),
    width: 150,
    height: 50,
  },
  backdrop: {
    zIndex: 3000,
    color: '#fff',
  },
}));
