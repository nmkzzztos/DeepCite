import { themes as prismThemes } from "prism-react-renderer";
import type { Config } from "@docusaurus/types";
import type * as Preset from "@docusaurus/preset-classic";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

const config: Config = {
  title: "Mind Notes",
  favicon: "img/logo_mini.svg",

  url: "https://github.com/",
  baseUrl: "/DeepCite/",

  organizationName: "deepcite",
  projectName: "deepcite",
  deploymentBranch: "gh-pages",
  trailingSlash: false,

  onBrokenLinks: "warn",
  onBrokenMarkdownLinks: "warn",

  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'de', 'ru'],
    localeConfigs: {
      en: {
        htmlLang: 'en-GB'
      },
      de: {
        htmlLang: 'de-DE'
      },
      ru: {
        htmlLang: 'ru-RU'
      },
    },
  },

  presets: [
    [
      "classic",
      {
        docs: {
          sidebarPath: "./sidebars.ts",
          editUrl: "https://github.com/nmkzzztos/deepcite/tree/main",
          remarkPlugins: [remarkMath],
          rehypePlugins: [rehypeKatex],
        },
        theme: {
          customCss: "./src/css/custom.css",
        },
      } satisfies Preset.Options,
    ],
  ],

  plugins: [
    [
      require.resolve("@easyops-cn/docusaurus-search-local"),
      /** @type {import("@easyops-cn/docusaurus-search-local").PluginOptions} */
      {
        // ... Your options.
        // `hashed` is recommended as long-term-cache of index file is possible.
        hashed: true,

        // For Docs using Chinese, it is recomended to set:
        // language: ["en", "de"],

        // If you're using `noIndex: true`, set `forceIgnoreNoIndex` to enable local index:
        // forceIgnoreNoIndex: true,
      },
    ],
  ],

  scripts: [
    '/js/math-copy.js',
  ],

  // stylesheets: [
  //   {
  //     href: 'https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css',
  //     type: 'text/css',
  //     integrity: 'sha384-GvrOXuhMATgEsSwCs4smul74iXGOixntILdUW9XmUC6+HX0sLNAK3q71HotJqlAn',
  //     crossorigin: 'anonymous',
  //   },
  // ],

  themeConfig: {
    image: "img/logo.svg",
    navbar: {
      logo: {
        src: "img/logo_mini.svg",
        srcDark: "img/logo_mini_white.svg",
        className: "header-logo",
        href: "/",
      },
      items: [
        {
          href: "/docs/introduction",
          label: "Docs",
          position: "left",
        },
        {
          href: "/papers",
          label: "Papers",
          position: "left",
        },
        {
          href: "/projects",
          label: "Projects",
          position: "left",
        },
        // {
        //   type: 'localeDropdown',
        //   position: 'right',
        // },
        {
          href: "https://github.com/nmkzzztos/DeepCite",
          position: "right",
          className: "header-github-link header-gitlab-link",
          "aria-label": "GitHub repository",
        },
      ],
    },
    footer: {
      style: "dark",
      links: [
        {
          items: [
            {
              label: "Github",
              href: "https://github.com/nmkzzztos",
              className: "footer__link-github",
            },
          ],
        },                                   
        {
          items: [
            {
              label: "LinkedIn",
              href: "https://www.linkedin.com/in/nmkzzztos/",
              className: "footer__link-linkedin",
            },
          ],
        },
      ],
      copyright: `© ${new Date().getFullYear()} Anton Guliaev | Powered by <a href="https://docusaurus.io/" target="_blank">Docusaurus</a>`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
