import { Container, Typography, Box } from '@mui/material'

function App() {
  return (
    <Container maxWidth="xl">
      <Box sx={{ my: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom>
          Apollonian Gasket Visualizer
        </Typography>
        <Typography variant="body1">
          Setup complete. Ready to build!
        </Typography>
      </Box>
    </Container>
  )
}

export default App
