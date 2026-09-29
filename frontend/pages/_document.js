import Document, { Html, Head, Main, NextScript } from 'next/document';

export default function MyDocument() {
  return (
    <Html lang="en">
      <Head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="description" content="Codessy — AI-powered cold email automation. Import recipients, personalize with AI, send from your own Gmail." />
        <meta name="theme-color" content="#232f3e" />
        <meta property="og:title" content="Codessy — Cold Email Automation" />
        <meta property="og:description" content="AI-personalized cold outreach from your own Gmail. Import spreadsheets, let AI research and write, then send." />
        <meta property="og:type" content="website" />
        <meta property="og:site_name" content="Codessy" />
        <meta name="twitter:card" content="summary_large_image" />
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('codessy-theme');if(!t&&window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches){t='dark';}if(t==='dark'){document.documentElement.setAttribute('data-theme','dark');}}catch(e){}})();`,
          }}
        />
      </Head>
      <body>
        <Main />
        <NextScript />
        <script src="https://checkout.razorpay.com/v1/checkout.js" async />
      </body>
    </Html>
  );
}
