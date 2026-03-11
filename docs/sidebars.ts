import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  tutorialSidebar: [
    'intro',
    {
      type: 'category',
      label: '快速开始',
      items: ['getting-started/installation', 'getting-started/quick-start'],
    },
    {
      type: 'category',
      label: '核心概念',
      items: [
        'core/concept',
        'core/strategy',
        'core/engine',
        'core/data',
      ],
    },
    {
      type: 'category',
      label: '进阶功能',
      items: [
        'advanced/risk-management',
        'advanced/optimization',
        'advanced/multi-asset',
      ],
    },
    {
      type: 'category',
      label: 'API 参考',
      items: ['api/overview'],
    },
  ],
};

export default sidebars;
