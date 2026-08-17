import '../styles/global.css';
import { AuthProvider } from '../lib/auth';
import { ToastProvider } from '../components/ui';

export default function App({ Component, pageProps }) {
  return (
    <AuthProvider>
      <ToastProvider>
        <Component {...pageProps} />
      </ToastProvider>
    </AuthProvider>
  );
}