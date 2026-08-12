export type Lang = "en" | "uz" | "ru";

type PlanT = {
  name: string;
  price: string;
  desc: string;
  cta: string;
  features: string[];
};

type AuthFormT = {
  title: string;
  subtitle: string;
  email: string;
  password: string;
  submit: string;
  submitting: string;
  forgotPassword: string;
  noAccount: string;
  createOne: string;
};

type SignupFormT = {
  title: string;
  subtitle: string;
  name: string;
  nameOptional: string;
  email: string;
  password: string;
  confirmPassword: string;
  submit: string;
  submitting: string;
  haveAccount: string;
  signIn: string;
};

type FPFormT = {
  title: string;
  subtitle: string;
  email: string;
  submit: string;
  submitting: string;
  success: string;
  backToLogin: string;
};

type RPFormT = {
  title: string;
  subtitle: string;
  password: string;
  confirmPassword: string;
  submit: string;
  submitting: string;
  success: string;
};

type VerifyT = {
  title: string;
  subtitle: string;
  success: string;
  invalid: string;
  resend: string;
};

type OAuthT = {
  google: string;
  github: string;
  working: string;
};

type DashNavT = {
  overview: string;
  businessPlan: string;
  bots: string;
  leads: string;
  knowledge: string;
  channels: string;
  analytics: string;
  billing: string;
  settings: string;
  marketingSite: string;
};

export type Translations = {
  nav: {
    features: string;
    pricing: string;
    faq: string;
    login: string;
    getStarted: string;
    dashboard: string;
    logout: string;
    language: string;
  };
  hero: {
    badge: string;
    headline: string;
    headlineAccent: string;
    subtext: string;
    cta: string;
    ctaSecondary: string;
    trustedBy: string;
  };
  stats: {
    bots: string;
    botsLabel: string;
    leads: string;
    leadsLabel: string;
    uptime: string;
    uptimeLabel: string;
  };
  howItWorks: {
    title: string;
    subtitle: string;
    steps: Array<{ title: string; desc: string }>;
  };
  features: {
    title: string;
    subtitle: string;
    items: Array<{ title: string; desc: string }>;
  };
  niches: {
    title: string;
    subtitle: string;
    loading: string;
  };
  pricing: {
    title: string;
    subtitle: string;
    perMonth: string;
    popular: string;
    free: string;
    plans: {
      free: PlanT;
      pro: PlanT;
      business: PlanT;
      enterprise: PlanT;
    };
  };
  faq: {
    title: string;
    subtitle: string;
    items: Array<{ q: string; a: string }>;
  };
  cta: {
    title: string;
    subtitle: string;
    button: string;
  };
  footer: {
    tagline: string;
    rights: string;
    contact: string;
    terms: string;
    privacy: string;
    product: string;
    legal: string;
  };
  auth: {
    login: AuthFormT;
    signup: SignupFormT;
    forgotPassword: FPFormT;
    resetPassword: RPFormT;
    verify: VerifyT;
    oauth: OAuthT;
    showPassword: string;
    hidePassword: string;
  };
  dashboard: {
    nav: DashNavT;
    topbar: {
      profile: string;
      settings: string;
      billing: string;
      logout: string;
    };
    overview: {
      title: string;
      subtitle: string;
      hi: string;
      hiAnon: string;
      welcomeLead: string;
      suggestedSteps: string;
      step1: string;
      step2: string;
      step3: string;
      quickActions: string;
      createBot: string;
      createBotHint: string;
      uploadKnowledge: string;
      uploadKnowledgeHint: string;
      connectChannel: string;
      connectChannelHint: string;
      activity: string;
      open: string;
      recentBots: string;
      recentBotsEmpty: string;
      recentBotsEmptyHint: string;
      recentLeads: string;
      recentLeadsEmpty: string;
      recentLeadsEmptyHint: string;
      channelStatus: string;
      channelStatusEmpty: string;
      channelStatusEmptyHint: string;
      createFirst: string;
      createFirstBody: string;
      createFirstBtn: string;
    };
    leads: {
      title: string;
      subtitle: string;
      count: string;
      countOne: string;
      filtered: string;
      showing: string;
      pipelineStatus: string;
      allStages: string;
      stNew: string;
      stContacted: string;
      stQualified: string;
      stProposal: string;
      stWon: string;
      stLost: string;
      temperature: string;
      anyTemp: string;
      tempCold: string;
      tempWarm: string;
      tempHot: string;
      nicheId: string;
      nichePlaceholder: string;
      toolbarHint: string;
      colLead: string;
      colStatus: string;
      colTemp: string;
      colScore: string;
      colNiche: string;
      colPhone: string;
      colCreated: string;
      loadMore: string;
      loadingMore: string;
      emptyTitle: string;
      emptyBody: string;
      emptyCta: string;
      emptyFilterTitle: string;
      emptyFilterBody: string;
      emptyApiTitle: string;
      emptyApiBody: string;
      retry: string;
      statsTotal: string;
      statsNew: string;
      statsQualified: string;
      statsWon: string;
      statsLost: string;
      statsCold: string;
      statsWarm: string;
      statsHot: string;
      detailBack: string;
      detailSummary: string;
      detailSummaryEmpty: string;
      detailCollected: string;
      detailCollectedEmpty: string;
      detailDetails: string;
      detailCurrentStatus: string;
      detailPhone: string;
      detailSource: string;
      detailCreated: string;
      detailUpdated: string;
      detailPipeline: string;
      detailPipelineHint: string;
      detailNoTemp: string;
      detailNotes: string;
      detailNotesPlaceholder: string;
      detailAssignee: string;
      detailSaving: string;
      detailSave: string;
      detailLoadError: string;
      detailLoading: string;
    };
    botDetail: {
      tabSettings: string;
      tabKnowledge: string;
      tabWidget: string;
      tabTelegram: string;
      subtitle: string;
      backToBots: string;
      loadingBot: string;
      loadError: string;
      retry: string;
      niche: string;
      goal: string;
      currentStatus: string;
      lastUpdated: string;
      name: string;
      status: string;
      tone: string;
      language: string;
      welcomeMessage: string;
      shortDescription: string;
      statusDraft: string;
      statusActive: string;
      statusPaused: string;
      statusArchived: string;
      tonePlaceholder: string;
      languagePlaceholder: string;
      welcomePlaceholder: string;
      shortDescPlaceholder: string;
      modelPlaceholder: string;
      defaultPlaceholder: string;
      aiResponseTitle: string;
      aiResponseHint: string;
      inferenceProvider: string;
      inferenceProviderHint: string;
      model: string;
      modelHint: string;
      temperature: string;
      temperatureHint: string;
      maxTokens: string;
      maxTokensHint: string;
      temperatureInvalid: string;
      maxTokensInvalid: string;
      archiveConfirmText: string;
      archiving: string;
      confirmArchive: string;
      cancel: string;
      saving: string;
      saveChanges: string;
      alreadyArchived: string;
      archiveBot: string;
      deletePermanently: string;
      deleteConfirmText: string;
      deleting: string;
      confirmDelete: string;
      testChatArchived: string;
    };
    botTelegram: {
      lead: string;
      loading: string;
      loadError: string;
      retry: string;
      upgradeTitle: string;
      upgradeDesc: string;
      upgradeBtn: string;
      botfatherTitle: string;
      botfatherIntro: string;
      botfatherRun: string;
      botfatherSelect: string;
      apiToken: string;
      botfatherFormat: string;
      botfatherPaste: string;
      neverShow: string;
      botfatherEnd: string;
      connectionTitle: string;
      pillActive: string;
      pillValidationFailed: string;
      pillSetupInProgress: string;
      pillNotStarted: string;
      webhookRegistered: string;
      botUsernamePrefix: string;
      usernameAfterConfirm: string;
      usernameConnect: string;
      lastVerifiedPrefix: string;
      archivedNotice: string;
      lastIssuePrefix: string;
      botTokenLabel: string;
      botTokenHint: string;
      tokenPlaceholderStored: string;
      tokenPlaceholderEmpty: string;
      connecting: string;
      updateConnection: string;
      connectTelegram: string;
      disconnecting: string;
      disconnect: string;
    };
    botWidget: {
      lead: string;
      loading: string;
      loadError: string;
      retry: string;
      settingsTitle: string;
      settingsHint: string;
      enabledTitle: string;
      enabledMeta: string;
      allowedDomains: string;
      domainsHint: string;
      welcomeLabel: string;
      welcomePlaceholder: string;
      themeLabel: string;
      themeAuto: string;
      themeLight: string;
      themeDark: string;
      themeHint: string;
      saving: string;
      saveBtn: string;
      installTitle: string;
      installHint: string;
      publicKeyLabel: string;
      checklistBuild: string;
      checklistHost: string;
      checklistHostSetPre: string;
      checklistHostSetPost: string;
      checklistHostConfigured: string;
      checklistApiPre: string;
      checklistApiMid: string;
      checklistApiPost: string;
      embedSnippet: string;
      copySnippet: string;
      copied: string;
      copyError: string;
    };
    bots: {
      title: string;
      subtitle: string;
      createBtn: string;
      search: string;
      searchPlaceholder: string;
      status: string;
      allStatuses: string;
      statusDraft: string;
      statusActive: string;
      statusPaused: string;
      statusArchived: string;
      statusChannelPending: string;
      toolbarHint: string;
      colName: string;
      colNiche: string;
      colGoal: string;
      colStatus: string;
      colUpdated: string;
      colActions: string;
      clone: string;
      cloning: string;
      emptyTitle: string;
      emptyBody: string;
      emptyApiNote: string;
      emptyCta: string;
      retry: string;
      loading: string;
    };
    analytics: {
      title: string;
      subtitle: string;
      period: string;
      periodDays: string;
      loading: string;
      noData: string;
      loadError: string;
      totalBots: string;
      activeCount: string;
      totalLeads: string;
      lastDays: string;
      hotLeads: string;
      highIntent: string;
      wonLeads: string;
      convRate: string;
      leadPipeline: string;
      leadTemperature: string;
      botStatus: string;
      planUsage: string;
      noLeadsYet: string;
      noBotsYet: string;
      createOne: string;
      stNew: string;
      stContacted: string;
      stQualified: string;
      stProposal: string;
      stWon: string;
      stLost: string;
      tempHot: string;
      tempWarm: string;
      tempCold: string;
      tempUnknown: string;
      botActive: string;
      botDraft: string;
      botPaused: string;
      botArchived: string;
      total: string;
      leads: string;
      plan: string;
      conversationsMonth: string;
      unlimited: string;
      of: string;
      billingHint: string;
      billingLink: string;
    };
    billing: {
      title: string;
      subtitle: string;
      loading: string;
      loadError: string;
      checkoutSuccess: string;
      checkoutCanceled: string;
      stripeNotConfigured: string;
      checkoutFailed: string;
      noStripeLinked: string;
      portalUnavailable: string;
      currentPlan: string;
      planLabel: string;
      perMonth: string;
      activeSub: string;
      renews: string;
      convPerMonth: string;
      bots: string;
      pdfFiles: string;
      storage: string;
      unlimited: string;
      manageBilling: string;
      opening: string;
      availablePlans: string;
      mostPopular: string;
      free: string;
      currentPlanBtn: string;
      contactSupport: string;
      upgrade: string;
      redirecting: string;
      manage: string;
      conversations: string;
      bot: string;
      storageUnit: string;
      statusActive: string;
      statusTrialing: string;
      statusPastDue: string;
      statusCanceled: string;
      statusExpired: string;
      contactUs: string;
    };
    settings: {
      title: string;
      subtitle: string;
      loading: string;
      // Profile
      profile: string;
      emailVerified: string;
      emailUnverified: string;
      active: string;
      inactive: string;
      userId: string;
      memberSince: string;
      lastUpdated: string;
      displayNamePlaceholder: string;
      saving: string;
      save: string;
      cancel: string;
      editDisplayName: string;
      nameUpdated: string;
      // Account Security
      accountSecurity: string;
      emailVerifiedMsg: string;
      emailUnverifiedMsg: string;
      sending: string;
      resendVerification: string;
      changePasswordHint: string;
      changePassword: string;
      passwordResetSent: string;
      currentPassword: string;
      newPassword: string;
      confirmNewPassword: string;
      passwordsDoNotMatch: string;
      passwordTooShort: string;
      passwordChanged: string;
      changingPassword: string;
      wrongCurrentPassword: string;
      verificationSent: string;
      // 2FA
      twoFactor: string;
      twoFactorActivated: string;
      twoFactorDisableConfirm: string;
      twoFactorDisabled: string;
      twoFactorProtected: string;
      disable2fa: string;
      disabling: string;
      scanQrCode: string;
      manualEntryKey: string;
      recoveryCodes: string;
      totpPlaceholder: string;
      verifying: string;
      activate: string;
      twoFactorDesc: string;
      settingUp: string;
      setUp2fa: string;
      // Sessions
      activeSessions: string;
      loadingSessions: string;
      noSessions: string;
      started: string;
      lastUsed: string;
      // Workspace
      workspace: string;
      billingPlans: string;
      manageBots: string;
      // Data & Privacy
      dataPrivacy: string;
      exportDesc: string;
      exporting: string;
      exportData: string;
      exportSuccess: string;
      // Danger Zone
      dangerZone: string;
      logoutAllDesc: string;
      signingOut: string;
      signOutAll: string;
      logoutAllConfirm: string;
      deleteAccountDesc: string;
      cannotBeUndone: string;
      absolutelySure: string;
      deleting: string;
      yesDelete: string;
      deleteAccount: string;
      // Telegram linking
      telegramTitle: string;
      telegramDesc: string;
      telegramLink: string;
      telegramLinkedMsg: string;
      telegramLinkedAt: string;
      telegramConnected: string;
      telegramUnlink: string;
      telegramUnlinking: string;
      telegramNotConfigured: string;
    };
    notifications: {
      title: string;
      bell: string;
      empty: string;
      markAllRead: string;
    };
    wizard: {
      title: string;
      lead: string;
      assistiveHint: string;
      loading: string;
      step: string;
      of: string;
      // Nav
      back: string;
      continue: string;
      exitToBots: string;
      skipForNow: string;
      createBot: string;
      creatingBot: string;
      // Step labels
      stepNiche: string;
      stepGoal: string;
      stepBasics: string;
      stepChannel: string;
      stepKnowledge: string;
      stepReview: string;
      // Step titles & descs
      nicheTitle: string;
      nicheDesc: string;
      goalTitle: string;
      goalDesc: string;
      basicsTitle: string;
      basicsDesc: string;
      channelTitle: string;
      channelDesc: string;
      knowledgeTitle: string;
      knowledgeDesc: string;
      reviewTitle: string;
      reviewDesc: string;
      // Niche
      nicheLoading: string;
      nicheLegend: string;
      nicheFallback: string;
      // Goal
      goalLegend: string;
      goalSupport: string;
      goalSupportHint: string;
      goalSales: string;
      goalSalesHint: string;
      goalFaq: string;
      goalFaqHint: string;
      goalConsulting: string;
      goalConsultingHint: string;
      // Basics
      botName: string;
      botNameHelp: string;
      botNamePlaceholder: string;
      toneLegend: string;
      toneHelp: string;
      toneFriendly: string;
      toneProfessional: string;
      tonePlayful: string;
      toneNeutral: string;
      languageLabel: string;
      languageHelp: string;
      shortDesc: string;
      shortDescPlaceholder: string;
      openingLine: string;
      openingLineHelp: string;
      defaultWelcome: string;
      optional: string;
      // Channel
      channelHint: string;
      channelLegend: string;
      chWebsite: string;
      chWebsiteHint: string;
      chTelegram: string;
      chTelegramHint: string;
      chBoth: string;
      chBothHint: string;
      proPlus: string;
      upgradeForTelegram: string;
      telegramRequiresPro: string;
      upgradeNow: string;
      telegramToken: string;
      telegramTokenHelp: string;
      telegramTokenPlaceholder: string;
      channelPending: string;
      // Knowledge
      knowledgeHint: string;
      typicalSources: string;
      srcPdf: string;
      srcFaq: string;
      srcService: string;
      srcPricing: string;
      pdfLiveTitle: string;
      pdfLiveBody: string;
      notesLabel: string;
      notesHelp: string;
      notesPlaceholder: string;
      // Upload zone
      uploadDropTitle: string;
      uploadDropMeta: string;
      removeFile: string;
      fileTooLarge: string;
      fileNotPdf: string;
      pendingUploadNote: string;
      // Review - files
      revFiles: string;
      noFilesAttached: string;
      filesReady: string;
      // Completion - upload
      uploadingFiles: string;
      uploadComplete: string;
      uploadPartialFail: string;
      // Review
      revNiche: string;
      revGoal: string;
      revName: string;
      revLanguage: string;
      revTone: string;
      revChannel: string;
      revTelegramToken: string;
      revKnowledge: string;
      tokenNA: string;
      tokenProvided: string;
      tokenNotProvided: string;
      knowledgeSkipped: string;
      knowledgeNone: string;
      expectedStatus: string;
      // Outcomes
      outcomeActiveWeb: string;
      outcomeActiveWebDetail: string;
      outcomeActiveTg: string;
      outcomeActiveTgDetail: string;
      outcomePending: string;
      outcomePendingDetail: string;
      outcomeDraft: string;
      outcomeDraftDetail: string;
      // Completion
      doneActiveTitle: string;
      doneActiveBody: string;
      donePendingTitle: string;
      donePendingBody: string;
      doneDefaultTitle: string;
      doneDefaultBody: string;
      serverStatus: string;
      primaryChannel: string;
      openBots: string;
    };
  };
  superadmin: {
    nav: {
      overview: string;
      users: string;
      bots: string;
      billing: string;
      aiUsage: string;
      auditLog: string;
      featureFlags: string;
      support: string;
      coupons: string;
      analytics: string;
      abuse: string;
      export: string;
      campaigns: string;
      webhookLogs: string;
    };
    common: {
      loading: string;
      error: string;
      save: string;
      saving: string;
      cancel: string;
      create: string;
      edit: string;
      delete: string;
      deleting: string;
      confirm: string;
      total: string;
      noRecords: string;
      actions: string;
      status: string;
      period: string;
      allStatuses: string;
      allPlans: string;
      allTypes: string;
      allActions: string;
      clear: string;
      view: string;
      back: string;
    };
    flags: {
      total: string;
      newFlag: string;
      key: string;
      state: string;
      plan: string;
      description: string;
      updated: string;
      enabled: string;
      disabled: string;
      toggleTitle: string;
      createTitle: string;
      editTitle: string;
      keyLabel: string;
      keyHelp: string;
      keyPlaceholder: string;
      descLabel: string;
      descPlaceholder: string;
      targetPlan: string;
      globalAllPlans: string;
      enableOnCreate: string;
      deleteTitle: string;
      deleteConfirm: string;
      deleteWarn: string;
      yesDelete: string;
      emptyState: string;
      targetUsers: string;
      targetUsersHelp: string;
      addEmail: string;
      emailPlaceholder: string;
      usersTargeted: string;
      noUserTarget: string;
      invalidEmail: string;
    };
    billing: {
      user: string;
      plan: string;
      periodStart: string;
      periodEnd: string;
      canceled: string;
      stripe: string;
      changePlan: string;
      changePlanTitle: string;
      newPlan: string;
      reason: string;
      reasonPlaceholder: string;
      blocked: string;
      manual: string;
      free: string;
      statusActive: string;
      statusTrialing: string;
      statusPastDue: string;
      statusCanceled: string;
      statusExpired: string;
      totalActive: string;
      totalPastDue: string;
      estimatedMrr: string;
      mrrNote: string;
    };
    aiUsage: {
      periodLabel: string;
      summaryTitle: string;
      totalCalls: string;
      successful: string;
      failed: string;
      successRate: string;
      totalTokens: string;
      totalCost: string;
      dailyHistory: string;
      date: string;
      calls: string;
      tokens: string;
      costUsd: string;
      topConsumers: string;
      user: string;
      cost: string;
      noData: string;
    };
    auditLog: {
      time: string;
      action: string;
      entityType: string;
      actor: string;
      meta: string;
      snapshot: string;
      snapshotTitle: string;
      before: string;
      after: string;
      metadata: string;
      sinceDate: string;
    };
    export: {
      intro: string;
      download: string;
      downloading: string;
      downloadFailed: string;
      usersLabel: string;
      usersDesc: string;
      subscriptionsLabel: string;
      subscriptionsDesc: string;
      aiUsageLabel: string;
      aiUsageDesc: string;
      couponsLabel: string;
      couponsDesc: string;
      quickPresets: string;
      preset7d: string;
      preset30d: string;
      preset90d: string;
      presetYtd: string;
    };
    overview: {
      intro: string;
      loadingOverview: string;
      usersAndBots: string;
      registeredUsers: string;
      activeUsers: string;
      totalBots: string;
      activeBots: string;
      leads: string;
      conversations: string;
      billingRevenue: string;
      mrr: string;
      mrrSub: string;
      paidActive: string;
      paidActiveSub: string;
      freePlan: string;
      freePlanSub: string;
      pastDue: string;
      pastDueSub: string;
      canceled: string;
      canceledSub: string;
      planDistribution: string;
      generatedAt: string;
      viewBilling: string;
      planChart: string;
      autoRefresh: string;
      refreshEvery: string;
      seconds: string;
      recentActivity: string;
    };
    users: {
      intro: string;
      showingRange: string;
      noUsers: string;
      selected: string;
      suspend: string;
      activate: string;
      applyTo: string;
      previous: string;
      next: string;
      selectAll: string;
      email: string;
      role: string;
      status: string;
      bots: string;
      updated: string;
      inactive: string;
      suspended: string;
      active: string;
      confirmBulkTitle: string;
      confirmBulkHint: string;
      reasonOptional: string;
      reasonPlaceholder: string;
      processing: string;
      confirmAction: string;
      bulkSuccess: string;
    };
    botsList: {
      intro: string;
      showingRange: string;
      noBots: string;
      previous: string;
      next: string;
      bot: string;
      owner: string;
      status: string;
      channels: string;
      updated: string;
      platformSuspended: string;
      widget: string;
      telegram: string;
      selected: string;
      bulkSuspend: string;
      bulkActivate: string;
      bulkSuspendTitle: string;
      bulkActivateTitle: string;
      bulkApplyTo: string;
      botsCount: string;
      bulkReason: string;
      bulkReasonPlaceholder: string;
    };
    userDetail: {
      loadingUser: string;
      backToUsers: string;
      inspectTenant: string;
      email: string;
      name: string;
      role: string;
      active: string;
      verified: string;
      password: string;
      suspendedAt: string;
      suspensionNote: string;
      oauthProviders: string;
      bots: string;
      created: string;
      updated: string;
      yes: string;
      no: string;
      set: string;
      notSet: string;
      activateUser: string;
      cannotSuspendSelf: string;
      suspendUser: string;
      impersonation: string;
      impersonationDesc: string;
      generating: string;
      generateToken: string;
      tokenHint: string;
      copy: string;
      dismiss: string;
      planOverride: string;
      plan: string;
      reasonOptional: string;
      reasonPlaceholder: string;
      applying: string;
      applyOverride: string;
      userSuspended: string;
      userActivated: string;
      planOverridden: string;
      suspendTitle: string;
      suspendDesc: string;
      suspendConfirm: string;
    };
    botDetail: {
      loadingBot: string;
      backToBots: string;
      name: string;
      botId: string;
      ownerEmail: string;
      ownerId: string;
      niche: string;
      goal: string;
      status: string;
      providerModel: string;
      widget: string;
      telegram: string;
      platformSuspended: string;
      suspensionNote: string;
      welcome: string;
      tone: string;
      language: string;
      description: string;
      temperature: string;
      maxOutputTokens: string;
      created: string;
      updated: string;
      configured: string;
      notConfigured: string;
      connected: string;
      notConnected: string;
      clearSuspension: string;
      platformSuspendBot: string;
      botSuspended: string;
      suspensionCleared: string;
      suspendBotTitle: string;
      suspendBotDesc: string;
      suspendBotConfirm: string;
      performance: string;
      conversations: string;
      leadsGenerated: string;
      aiCalls: string;
      aiTokens: string;
    };
    support: {
      loadError: string;
      updateError: string;
      allStatuses: string;
      statusOpen: string;
      statusInProgress: string;
      statusResolved: string;
      statusClosed: string;
      allPriorities: string;
      priorityLow: string;
      priorityNormal: string;
      priorityHigh: string;
      ticketsCount: string;
      subject: string;
      user: string;
      status: string;
      priority: string;
      created: string;
      actions: string;
      noTickets: string;
      notePrefix: string;
      edit: string;
      prevPage: string;
      nextPage: string;
      pageOf: string;
      updateTitle: string;
      statusLabel: string;
      priorityLabel: string;
      adminNote: string;
      notePlaceholder: string;
      cancel: string;
      saving: string;
      save: string;
      replyTitle: string;
      ticketBody: string;
      replyLabel: string;
      replyPlaceholder: string;
      replyAndProgress: string;
      replyAndResolve: string;
      submittedAt: string;
      resolvedAt: string;
      noReplyYet: string;
      previousReply: string;
    };
    abuse: {
      loadError: string;
      suspendError: string;
      periodLabel: string;
      day1: string;
      day3: string;
      day7: string;
      minCalls: string;
      refresh: string;
      highUsageTitle: string;
      user: string;
      calls: string;
      failed: string;
      tokens: string;
      cost: string;
      errorRate: string;
      actions: string;
      noHighUsage: string;
      suspend: string;
      topErrorsTitle: string;
      errorCode: string;
      occurrences: string;
      noErrors: string;
      suspendedUser: string;
      failedToSuspend: string;
    };
    campaigns: {
      segmentAllUsers: string;
      segmentPastDue: string;
      segmentFreePlan: string;
      segmentPaidUsers: string;
      segmentInactive7d: string;
      loadError: string;
      createError: string;
      updateError: string;
      sendError: string;
      deleteError: string;
      newCampaign: string;
      campaignsCount: string;
      subject: string;
      segment: string;
      status: string;
      sentFailed: string;
      sentAt: string;
      actions: string;
      noCampaigns: string;
      recipients: string;
      failedCount: string;
      preview: string;
      edit: string;
      send: string;
      delete: string;
      prevPage: string;
      nextPage: string;
      pageOf: string;
      newTitle: string;
      subjectLabel: string;
      targetSegment: string;
      bodyLabel: string;
      cancel: string;
      creating: string;
      createDraft: string;
      editTitle: string;
      bodyHtml: string;
      saving: string;
      saveChanges: string;
      previewTitle: string;
      segmentLabel: string;
      close: string;
      sendTitle: string;
      sendConfirm: string;
      sending: string;
      confirmSend: string;
      deleteTitle: string;
      deleteConfirm: string;
      deleting: string;
      campaignCreated: string;
      campaignUpdated: string;
      campaignSending: string;
      templateLabel: string;
      tplBlank: string;
      tplBlankDesc: string;
      tplWelcome: string;
      tplWelcomeDesc: string;
      tplAnnouncement: string;
      tplAnnouncementDesc: string;
      tplPromotion: string;
      tplPromotionDesc: string;
      tplReengagement: string;
      tplReengagementDesc: string;
    };
    coupons: {
      loadError: string;
      createError: string;
      updateError: string;
      deleteError: string;
      codeExists: string;
      newCoupon: string;
      couponsCount: string;
      code: string;
      discount: string;
      plan: string;
      uses: string;
      expires: string;
      status: string;
      actions: string;
      noCoupons: string;
      allPlans: string;
      active: string;
      inactive: string;
      edit: string;
      delete: string;
      createTitle: string;
      codeLabel: string;
      typeLabel: string;
      valueLabel: string;
      percentType: string;
      usdType: string;
      targetPlan: string;
      maxUses: string;
      expiresAt: string;
      cancel: string;
      creating: string;
      create: string;
      editTitle: string;
      activeLabel: string;
      inactiveLabel: string;
      clearExpiry: string;
      saving: string;
      save: string;
      deleteTitle: string;
      deleteConfirm: string;
      deleting: string;
      couponCreated: string;
      analyticsActive: string;
      analyticsRedemptions: string;
      analyticsExpired: string;
      analyticsMaxedOut: string;
      analyticsAvgDiscount: string;
    };
    webhooks: {
      loadError: string;
      failedTotal: string;
      showFailedOnly: string;
      allSources: string;
      stripe: string;
      telegram: string;
      allStatuses: string;
      received: string;
      processed: string;
      failed: string;
      clearDates: string;
      logsCount: string;
      source: string;
      eventType: string;
      status: string;
      bot: string;
      receivedAt: string;
      details: string;
      noLogs: string;
      view: string;
      prevPage: string;
      nextPage: string;
      pageOf: string;
      close: string;
    };
    tenant: {
      loadingInspection: string;
      backToUser: string;
      intro: string;
      leads: string;
      conversations: string;
      aiCalls: string;
      aiFailures: string;
      tokensWindow: string;
      tenantSummary: string;
      email: string;
      role: string;
      active: string;
      botsProfile: string;
      yes: string;
      no: string;
      channelMix: string;
      noConversations: string;
      channel: string;
      botsShown: string;
      noBotsForTenant: string;
      bot: string;
      status: string;
      channels: string;
      widget: string;
      telegram: string;
      aiUsageWindow: string;
      dailyRollup: string;
      noDailyData: string;
      date: string;
      requests: string;
      tokens: string;
      costUsd: string;
      recentErrors: string;
      noFailedCalls: string;
      when: string;
      model: string;
      code: string;
    };
    analytics: {
      channelWebWidget: string;
      channelTelegram: string;
      channelAdminTest: string;
      loadError: string;
      periodLabel: string;
      channelDistribution: string;
      noConversationData: string;
      userSignups: string;
      noSignupData: string;
      date: string;
      newUsers: string;
      bar: string;
      planSegments: string;
      plan: string;
      status: string;
      count: string;
      churnByPlan: string;
      canceled: string;
      noChurnData: string;
      botsByNiche: string;
      niche: string;
      bots: string;
      noData: string;
      botsByGoal: string;
      goal: string;
      signupChart: string;
      channelChart: string;
    };
    moderation: {
      internalNote: string;
      internalNotePlaceholder: string;
      cancel: string;
    };
  };
  common: {
    loading: string;
    error: string;
    save: string;
    cancel: string;
    delete: string;
    edit: string;
    back: string;
    next: string;
    finish: string;
    optional: string;
    or: string;
  };
};

const en: Translations = {
  nav: {
    features: "Features",
    pricing: "Pricing",
    faq: "FAQ",
    login: "Log in",
    getStarted: "Get Started",
    dashboard: "Dashboard",
    logout: "Log out",
    language: "Language",
  },
  hero: {
    badge: "AI Lead Generation Platform",
    headline: "Turn Visitors Into",
    headlineAccent: "Real Clients",
    subtext:
      "Create a smart AI bot that talks to visitors, qualifies their needs, and delivers them as leads — on your website or Telegram. No code required.",
    cta: "Create Your Bot — Free",
    ctaSecondary: "See How It Works",
    trustedBy: "Trusted by businesses worldwide",
  },
  stats: {
    bots: "500+",
    botsLabel: "Active Bots",
    leads: "10K+",
    leadsLabel: "Leads Generated",
    uptime: "99.9%",
    uptimeLabel: "Uptime",
  },
  howItWorks: {
    title: "How It Works",
    subtitle: "From signup to your first qualified lead in minutes — nothing extra.",
    steps: [
      { title: "Sign Up", desc: "Create a free account in seconds." },
      { title: "Choose Your Niche", desc: "Tell the bot what you sell and who you help." },
      {
        title: "Upload Knowledge",
        desc: "Drop in PDFs or notes so answers sound like you.",
      },
      {
        title: "Connect Channel",
        desc: "Add widget to your site or connect your Telegram channel.",
      },
      {
        title: "Get Leads",
        desc: "Visitors chat, you get clean qualified leads to follow up.",
      },
    ],
  },
  features: {
    title: "Everything You Need",
    subtitle: "Your AI assistant handles conversations and delivers ready-to-close leads.",
    items: [
      {
        title: "Automatic Lead Capture",
        desc: "The bot collects names, phone numbers, and emails during the conversation — leads go straight to your dashboard.",
      },
      {
        title: "Answers From Your Knowledge Base",
        desc: "Upload your documents and the bot will answer customer questions based on your actual products and services.",
      },
      {
        title: "Works on Website & Telegram",
        desc: "Install a chat widget on your site or connect a Telegram bot — manage everything from one place.",
      },
      {
        title: "Launch in Minutes",
        desc: "Choose your business type, customize the style, and your bot is live — no developers needed.",
      },
    ],
  },
  niches: {
    title: "Built for Your Niche",
    subtitle: "Pick a starting point — tone and flows match how you already work.",
    loading: "Loading...",
  },
  pricing: {
    title: "Simple, Transparent Pricing",
    subtitle: "Start free. Upgrade when you grow.",
    perMonth: "/ mo",
    popular: "Most Popular",
    free: "Free",
    plans: {
      free: {
        name: "Free",
        price: "0",
        desc: "Try Phoenix AI with no commitment",
        cta: "Start Free",
        features: [
          "1 bot",
          "100 conversations/month",
          "Website widget",
          "1 PDF document",
          "Phoenix AI branding",
          "Community support",
        ],
      },
      pro: {
        name: "Pro",
        price: "39",
        desc: "For businesses ready to capture leads at scale",
        cta: "Get Pro",
        features: [
          "5 bots",
          "5,000 conversations/month",
          "Website + Telegram",
          "25 PDF documents",
          "Remove branding",
          "Analytics dashboard",
          "Email support",
        ],
      },
      business: {
        name: "Business",
        price: "99",
        desc: "For teams that need full power and flexibility",
        cta: "Get Business",
        features: [
          "Unlimited bots",
          "20,000 conversations/month",
          "All channels",
          "Unlimited documents",
          "API access",
          "5 team members",
          "Advanced analytics",
          "Priority support",
        ],
      },
      enterprise: {
        name: "Enterprise",
        price: "Contact Us",
        desc: "Custom volume, SLA, and dedicated support",
        cta: "Contact Us",
        features: [
          "Everything in Business",
          "Unlimited conversations",
          "Custom SLA",
          "Dedicated account manager",
          "Custom integrations",
          "On-premise option",
        ],
      },
    },
  },
  faq: {
    title: "Frequently Asked Questions",
    subtitle: "Answers to the most common questions from our customers.",
    items: [
      {
        q: "How does the bot know what to say to my customers?",
        a: "You upload your documents (price lists, FAQs, service descriptions) and the bot learns from them. It only answers based on your real information, not generic responses.",
      },
      {
        q: "What happens if the bot cannot answer a question?",
        a: "The bot politely tells the customer it will pass the question to a real person, and the conversation is flagged in your dashboard so you can follow up.",
      },
      {
        q: "Can I see the conversations and leads the bot collects?",
        a: "Yes. Every conversation, collected contact, and lead is visible in your dashboard in real time. You can filter, export, and track everything.",
      },
      {
        q: "How do I add the bot to my website?",
        a: "Copy one line of code and paste it into your site. Works with any website builder — WordPress, Tilda, Wix, or custom HTML. Takes under 2 minutes.",
      },
      {
        q: "Does the bot work in multiple languages?",
        a: "Yes. The bot automatically detects the language your visitor writes in and responds in the same language. It supports English, Russian, Uzbek, Turkish, Arabic, and many more.",
      },
      {
        q: "Can I try it before paying?",
        a: "Absolutely. The Free plan gives you 1 bot with 100 conversations per month — no credit card required. Upgrade only when you need more.",
      },
      {
        q: "Is my customer data safe?",
        a: "All data is encrypted in transit and at rest. We do not sell your data or use it to train AI models. You can delete all your data at any time.",
      },
    ],
  },
  cta: {
    title: "Ready to get more leads?",
    subtitle: "Join hundreds of businesses already using Phoenix AI.",
    button: "Create Free Account",
  },
  footer: {
    tagline: "AI chatbots that turn your visitors into real customers.",
    rights: "All rights reserved.",
    contact: "Contact",
    terms: "Terms",
    privacy: "Privacy",
    product: "Product",
    legal: "Legal",
  },
  auth: {
    login: {
      title: "Welcome Back",
      subtitle: "Sign in to your Phoenix AI workspace.",
      email: "Email",
      password: "Password",
      submit: "Sign In",
      submitting: "Signing in...",
      forgotPassword: "Forgot password?",
      noAccount: "No account?",
      createOne: "Create one",
    },
    signup: {
      title: "Create Account",
      subtitle: "Start building with Phoenix AI.",
      name: "Full Name",
      nameOptional: "(optional)",
      email: "Email",
      password: "Password",
      confirmPassword: "Confirm Password",
      submit: "Create Account",
      submitting: "Creating account...",
      haveAccount: "Have an account?",
      signIn: "Sign in",
    },
    forgotPassword: {
      title: "Reset Password",
      subtitle: "Enter your email and we'll send you a reset link.",
      email: "Email",
      submit: "Send Reset Link",
      submitting: "Sending...",
      success:
        "Check your inbox — we sent you a reset link if this email is registered.",
      backToLogin: "Back to sign in",
    },
    resetPassword: {
      title: "Set New Password",
      subtitle: "Choose a strong password for your account.",
      password: "New Password",
      confirmPassword: "Confirm New Password",
      submit: "Reset Password",
      submitting: "Resetting...",
      success: "Password updated! You can now sign in.",
    },
    verify: {
      title: "Verify Your Email",
      subtitle: "Check your inbox for a verification link.",
      success: "Email verified! Redirecting...",
      invalid: "This verification link is invalid or has expired.",
      resend: "Resend verification email",
    },
    oauth: {
      google: "Continue with Google",
      github: "Continue with GitHub",
      working: "Completing sign-in...",
    },
    showPassword: "Show password",
    hidePassword: "Hide password",
  },
  dashboard: {
    nav: {
      overview: "Overview",
      businessPlan: "Business plan",
      bots: "Bots",
      leads: "Leads",
      knowledge: "Knowledge",
      channels: "Channels",
      analytics: "Analytics",
      billing: "Billing",
      settings: "Settings",
      marketingSite: "← Marketing site",
    },
    topbar: {
      profile: "Profile",
      settings: "Settings",
      billing: "Billing",
      logout: "Log out",
    },
    overview: {
      title: "Dashboard",
      subtitle: "Your workspace overview",
      hi: "Hi",
      hiAnon: "Welcome",
      welcomeLead: "Here's your workspace at a glance. Create a bot, upload knowledge, and connect a channel to start capturing leads.",
      suggestedSteps: "Getting started",
      step1: "Create your first bot and set up its tone and behavior.",
      step2: "Upload documents so your bot gives accurate answers.",
      step3: "Connect a website widget or Telegram to go live.",
      quickActions: "Quick actions",
      createBot: "Create Bot",
      createBotHint: "Set up tone, prompts, and behavior.",
      uploadKnowledge: "Upload Knowledge",
      uploadKnowledgeHint: "Add PDFs, notes, or FAQs for your bot.",
      connectChannel: "Connect Channel",
      connectChannelHint: "Website widget, Telegram, or other integrations.",
      activity: "Your activity",
      open: "View all",
      recentBots: "Recent bots",
      recentBotsEmpty: "No bots yet",
      recentBotsEmptyHint: "Create your first bot to see it here.",
      recentLeads: "Recent leads",
      recentLeadsEmpty: "No leads yet",
      recentLeadsEmptyHint: "Leads will appear here once visitors start chatting with your bot.",
      channelStatus: "Channels",
      channelStatusEmpty: "No channels connected",
      channelStatusEmptyHint: "Connect a website widget or Telegram to start receiving messages.",
      createFirst: "Create your first bot",
      createFirstBody: "You don't have any bots yet. It only takes a minute to get started.",
      createFirstBtn: "Create Bot",
    },
    leads: {
      title: "Leads",
      subtitle: "Prospects captured through your bots — review stage, temperature, and contact details.",
      count: "leads",
      countOne: "lead",
      filtered: "(filtered)",
      showing: "Showing",
      pipelineStatus: "Pipeline status",
      allStages: "All stages",
      stNew: "New",
      stContacted: "Contacted",
      stQualified: "Qualified",
      stProposal: "Proposal",
      stWon: "Won",
      stLost: "Lost",
      temperature: "Temperature",
      anyTemp: "Any temperature",
      tempCold: "Cold",
      tempWarm: "Warm",
      tempHot: "Hot",
      nicheId: "Niche",
      nichePlaceholder: "e.g. education",
      toolbarHint: "Filters query the API in real time.",
      colLead: "Lead",
      colStatus: "Status",
      colTemp: "Temp",
      colScore: "Score",
      colNiche: "Niche",
      colPhone: "Phone",
      colCreated: "Created",
      loadMore: "Load more leads",
      loadingMore: "Loading...",
      emptyTitle: "No leads yet",
      emptyBody: "When visitors chat with your bots, qualified leads will appear here for follow-up.",
      emptyCta: "Go to bots",
      emptyFilterTitle: "No leads match these filters",
      emptyFilterBody: "Try clearing pipeline status, temperature, or niche to see more results.",
      emptyApiTitle: "Leads API not available",
      emptyApiBody: "When the backend is deployed, your captured leads will appear here automatically.",
      retry: "Retry",
      statsTotal: "Total",
      statsNew: "New",
      statsQualified: "Qualified",
      statsWon: "Won",
      statsLost: "Lost",
      statsCold: "Cold",
      statsWarm: "Warm",
      statsHot: "Hot",
      detailBack: "Leads",
      detailSummary: "Summary",
      detailSummaryEmpty: "No summary captured for this lead.",
      detailCollected: "Collected data",
      detailCollectedEmpty: "No structured fields were stored.",
      detailDetails: "Details",
      detailCurrentStatus: "Current status",
      detailPhone: "Phone",
      detailSource: "Source",
      detailCreated: "Created",
      detailUpdated: "Updated",
      detailPipeline: "Pipeline & notes",
      detailPipelineHint: "Won and lost are final — only temperature and notes can change after that.",
      detailNoTemp: "No temperature",
      detailNotes: "Internal notes",
      detailNotesPlaceholder: "Call outcomes, next steps...",
      detailAssignee: "Assignee ID (UUID)",
      detailSaving: "Saving...",
      detailSave: "Save changes",
      detailLoadError: "Could not load this lead.",
      detailLoading: "Loading lead...",
    },
    botDetail: {
      tabSettings: "Settings & chat",
      tabKnowledge: "Knowledge",
      tabWidget: "Web widget",
      tabTelegram: "Telegram",
      subtitle: "Bot details, knowledge base, and test chat",
      backToBots: "Back to Bots",
      loadingBot: "Loading bot details...",
      loadError: "Could not load bot details.",
      retry: "Retry",
      niche: "Niche",
      goal: "Goal",
      currentStatus: "Current status",
      lastUpdated: "Last updated",
      name: "Name",
      status: "Status",
      tone: "Tone",
      language: "Language",
      welcomeMessage: "Welcome message",
      shortDescription: "Short description",
      statusDraft: "Draft",
      statusActive: "Active",
      statusPaused: "Paused",
      statusArchived: "Archived",
      tonePlaceholder: "Friendly and concise",
      languagePlaceholder: "en",
      welcomePlaceholder: "Hi! How can I help you today?",
      shortDescPlaceholder: "Describe what this bot handles.",
      modelPlaceholder: "Leave blank for default",
      defaultPlaceholder: "Default",
      aiResponseTitle: "AI response",
      aiResponseHint: "Optional tuning for generated replies. Leave fields blank to use platform defaults.",
      inferenceProvider: "Inference provider",
      inferenceProviderHint: "Managed by the platform for this workspace.",
      model: "Model",
      modelHint: "Provider-specific model id (letters, digits, dots, underscores, hyphens).",
      temperature: "Temperature",
      temperatureHint: "0 = more focused, 2 = more varied. Blank = provider default.",
      maxTokens: "Max output tokens",
      maxTokensHint: "Caps reply length. Blank = provider default.",
      temperatureInvalid: "Temperature must be a number between 0 and 2, or left blank for the default.",
      maxTokensInvalid: "Max output tokens must be a whole number from 1 to 8192, or left blank for the default.",
      archiveConfirmText: "Archive this bot? It will stay visible in your bots list with an archived status.",
      archiving: "Archiving...",
      confirmArchive: "Confirm archive",
      cancel: "Cancel",
      saving: "Saving...",
      saveChanges: "Save changes",
      alreadyArchived: "Already archived",
      archiveBot: "Archive bot",
      deletePermanently: "Delete permanently",
      deleteConfirmText: "Permanently delete this bot? This action cannot be undone. All associated data (knowledge base, conversations, leads) will be removed.",
      deleting: "Deleting...",
      confirmDelete: "Confirm delete",
      testChatArchived: "Test chat is unavailable while this bot is archived.",
    },
    botTelegram: {
      lead: "Let customers talk to this bot on Telegram. Messages use the same AI configuration as your dashboard test chat and web widget.",
      loading: "Loading Telegram settings…",
      loadError: "Could not load Telegram settings.",
      retry: "Retry",
      upgradeTitle: "Telegram integration requires a Pro plan or higher.",
      upgradeDesc: "Upgrade your plan to connect your bot to Telegram and reach customers on their favorite messenger.",
      upgradeBtn: "Upgrade Plan",
      botfatherTitle: "BotFather token",
      botfatherIntro: " — In Telegram, open ",
      botfatherRun: ", run ",
      botfatherSelect: " or select your bot, then copy the ",
      apiToken: "API token",
      botfatherFormat: " (format ",
      botfatherPaste: "). Paste it below once; we verify it with Telegram, encrypt it, and ",
      neverShow: "never show it again",
      botfatherEnd: " in this UI.",
      connectionTitle: "Connection",
      pillActive: "Active",
      pillValidationFailed: "Validation failed",
      pillSetupInProgress: "Setup in progress",
      pillNotStarted: "Not started",
      webhookRegistered: "Webhook registered",
      botUsernamePrefix: "Bot username: ",
      usernameAfterConfirm: "Username will appear here after Telegram confirms your bot.",
      usernameConnect: "Connect to see your bot's Telegram username.",
      lastVerifiedPrefix: "Last verified: ",
      archivedNotice: "This bot is archived. Connect and token actions are disabled. Disconnect is still available to remove stored credentials.",
      lastIssuePrefix: "Last issue: ",
      botTokenLabel: "Bot token",
      botTokenHint: "One-time entry. After a successful connect, clear the field yourself or we clear it on success — the API does not return the secret.",
      tokenPlaceholderStored: "Token saved — paste only to replace (connect again)",
      tokenPlaceholderEmpty: "Paste token from BotFather",
      connecting: "Connecting…",
      updateConnection: "Update connection",
      connectTelegram: "Connect Telegram",
      disconnecting: "Disconnecting…",
      disconnect: "Disconnect",
    },
    botWidget: {
      lead: "Add the chat widget to your site. Settings apply to the public embed; your secret keys stay on the server.",
      loading: "Loading widget settings…",
      loadError: "Could not load widget settings.",
      retry: "Retry",
      settingsTitle: "Widget settings",
      settingsHint: "Allowed domains restrict which websites may load this widget. Leave empty to allow any origin while you test—lock it down before production.",
      enabledTitle: "Widget enabled",
      enabledMeta: "When off, visitors cannot bootstrap or chat.",
      allowedDomains: "Allowed domains",
      domainsHint: "One hostname per line. Ports are not supported—use the host only.",
      welcomeLabel: "Widget welcome text",
      welcomePlaceholder: "Shown when the chat opens. Leave blank to rely on the bot default.",
      themeLabel: "Theme",
      themeAuto: "Auto (from visitor)",
      themeLight: "Light",
      themeDark: "Dark",
      themeHint: "Controls widget chrome; the embed respects this on the next load.",
      saving: "Saving…",
      saveBtn: "Save widget settings",
      installTitle: "Install",
      installHint: "Your public widget key is safe to embed in HTML. It only allows chat on domains you approve.",
      publicKeyLabel: "Public widget key",
      checklistBuild: "Build the widget bundle from the Phoenix AI embed package",
      checklistHost: "Host that file on your CDN or static server",
      checklistHostSetPre: " and set ",
      checklistHostSetPost: " in this app so the snippet below uses your hosted URL.",
      checklistHostConfigured: " (script URL is configured for this dashboard).",
      checklistApiPre: "Set ",
      checklistApiMid: " for this dashboard so the snippet includes your real API base (or replace ",
      checklistApiPost: " manually).",
      embedSnippet: "Embed snippet",
      copySnippet: "Copy snippet",
      copied: "Copied to clipboard.",
      copyError: "Could not copy—select the code or check browser permissions.",
    },
    bots: {
      title: "Your bots",
      subtitle: "Create, tune, and deploy bots for your customers.",
      createBtn: "Create Bot",
      search: "Search",
      searchPlaceholder: "Search bots by name...",
      status: "Status",
      allStatuses: "All statuses",
      statusDraft: "Draft",
      statusActive: "Active",
      statusPaused: "Paused",
      statusArchived: "Archived",
      statusChannelPending: "Channel pending",
      toolbarHint: "Search by name, niche, or goal. Filter by status.",
      colName: "Name",
      colNiche: "Niche",
      colGoal: "Goal",
      colStatus: "Status",
      colUpdated: "Last updated",
      colActions: "Actions",
      clone: "Clone",
      cloning: "Cloning...",
      emptyTitle: "No bots yet",
      emptyBody: "Create your first bot — set tone and prompts, add knowledge, and connect a channel.",
      emptyApiNote: "The bot list API is not reachable. You can still create a new bot.",
      emptyCta: "Create your first bot",
      retry: "Retry",
      loading: "Loading bots...",
    },
    analytics: {
      title: "Analytics",
      subtitle: "Track your bots, leads, and usage at a glance",
      period: "Period",
      periodDays: "d",
      loading: "Loading analytics…",
      noData: "No data available",
      loadError: "Failed to load analytics",
      totalBots: "Total bots",
      activeCount: "active",
      totalLeads: "Total leads",
      lastDays: "last",
      hotLeads: "Hot leads",
      highIntent: "high-intent",
      wonLeads: "Won leads",
      convRate: "conv. rate",
      leadPipeline: "Lead pipeline",
      leadTemperature: "Lead temperature",
      botStatus: "Bot status",
      planUsage: "Plan & usage",
      noLeadsYet: "No leads yet",
      noBotsYet: "No bots yet",
      createOne: "create one",
      stNew: "New",
      stContacted: "Contacted",
      stQualified: "Qualified",
      stProposal: "Proposal",
      stWon: "Won",
      stLost: "Lost",
      tempHot: "Hot",
      tempWarm: "Warm",
      tempCold: "Cold",
      tempUnknown: "Unknown",
      botActive: "Active",
      botDraft: "Draft",
      botPaused: "Paused",
      botArchived: "Archived",
      total: "total",
      leads: "leads",
      plan: "Plan",
      conversationsMonth: "Conversations this month",
      unlimited: "Unlimited",
      of: "of",
      billingHint: "View full limits and upgrade options on the",
      billingLink: "Billing page",
    },
    billing: {
      title: "Billing",
      subtitle: "Manage your subscription and plan limits",
      loading: "Loading billing info…",
      loadError: "Failed to load billing info",
      checkoutSuccess: "Your subscription has been activated. Welcome aboard!",
      checkoutCanceled: "Checkout was canceled. No changes were made to your plan.",
      stripeNotConfigured: "Payment system is not configured yet. Contact support.",
      checkoutFailed: "Checkout failed",
      noStripeLinked: "No Stripe account linked. Please subscribe to a paid plan first.",
      portalUnavailable: "Portal unavailable",
      currentPlan: "Current plan",
      planLabel: "Plan",
      perMonth: "/mo",
      activeSub: "Your active subscription",
      renews: "Renews",
      convPerMonth: "Conversations/mo",
      bots: "Bots",
      pdfFiles: "PDF files",
      storage: "Storage",
      unlimited: "Unlimited",
      manageBilling: "Manage billing",
      opening: "Opening…",
      availablePlans: "Available Plans",
      mostPopular: "Most popular",
      free: "Free",
      currentPlanBtn: "Current plan",
      contactSupport: "Contact support",
      upgrade: "Upgrade",
      redirecting: "Redirecting…",
      manage: "Manage",
      conversations: "conversations",
      bot: "bot",
      storageUnit: "storage",
      statusActive: "Active",
      statusTrialing: "Trialing",
      statusPastDue: "Past due",
      statusCanceled: "Canceled",
      statusExpired: "Expired",
      contactUs: "Contact us",
    },
    settings: {
      title: "Settings",
      subtitle: "Manage your profile, security, and account preferences",
      loading: "Loading...",
      // Profile
      profile: "Profile",
      emailVerified: "Email verified",
      emailUnverified: "Email unverified",
      active: "Active",
      inactive: "Inactive",
      userId: "User ID",
      memberSince: "Member since",
      lastUpdated: "Last updated",
      displayNamePlaceholder: "Display name",
      saving: "Saving...",
      save: "Save",
      cancel: "Cancel",
      editDisplayName: "Edit display name",
      nameUpdated: "Display name updated.",
      // Account Security
      accountSecurity: "Account security",
      emailVerifiedMsg: "Your email address has been verified.",
      emailUnverifiedMsg: "Your email is not yet verified. Verify it to enable all features.",
      sending: "Sending...",
      resendVerification: "Resend verification email",
      changePasswordHint: "Enter your current password and choose a new one (minimum 8 characters).",
      changePassword: "Change password",
      passwordResetSent: "Password reset link sent — check your inbox.",
      currentPassword: "Current password",
      newPassword: "New password",
      confirmNewPassword: "Confirm new password",
      passwordsDoNotMatch: "Passwords do not match",
      passwordTooShort: "Password must be at least 8 characters",
      passwordChanged: "Password changed successfully!",
      changingPassword: "Changing...",
      wrongCurrentPassword: "Current password is incorrect",
      verificationSent: "Verification email sent — check your inbox.",
      // 2FA
      twoFactor: "Two-factor authentication",
      twoFactorActivated: "Two-factor authentication activated!",
      twoFactorDisableConfirm: "Are you sure you want to disable two-factor authentication?",
      twoFactorDisabled: "Two-factor authentication disabled.",
      twoFactorProtected: "Your account is protected with TOTP.",
      disable2fa: "Disable 2FA",
      disabling: "Disabling...",
      scanQrCode: "Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.), then enter the code below.",
      manualEntryKey: "Manual entry key:",
      recoveryCodes: "Recovery codes (save these securely):",
      totpPlaceholder: "6-digit code",
      verifying: "Verifying...",
      activate: "Activate",
      twoFactorDesc: "Add an extra layer of security to your account by enabling two-factor authentication with an authenticator app.",
      settingUp: "Setting up...",
      setUp2fa: "Set up 2FA",
      // Sessions
      activeSessions: "Active sessions",
      loadingSessions: "Loading sessions...",
      noSessions: "No active sessions found.",
      started: "Started",
      lastUsed: "Last used",
      // Workspace
      workspace: "Workspace",
      billingPlans: "Billing & plans",
      manageBots: "Manage bots",
      // Data & Privacy
      dataPrivacy: "Data & Privacy",
      exportDesc: "Export a JSON snapshot of your account data — profile, bots, leads, and subscription info.",
      exporting: "Exporting...",
      exportData: "Export my data",
      exportSuccess: "Data exported successfully.",
      // Danger Zone
      dangerZone: "Danger zone",
      logoutAllDesc: "Signing out of all devices will immediately invalidate every active session, including this one. You will be redirected to the login page.",
      signingOut: "Signing out...",
      signOutAll: "Sign out all devices",
      logoutAllConfirm: "This will sign you out of all devices. Continue?",
      deleteAccountDesc: "Permanently delete your account and all associated data (bots, conversations, leads, files).",
      cannotBeUndone: "cannot be undone",
      absolutelySure: "Are you absolutely sure?",
      deleting: "Deleting...",
      yesDelete: "Yes, delete my account",
      deleteAccount: "Delete my account",
      // Telegram linking
      telegramTitle: "Telegram notifications",
      telegramDesc: "Link your Telegram account to receive instant lead alerts when your bots capture new leads.",
      telegramLink: "Link Telegram",
      telegramLinkedMsg: "Your Telegram account is linked. You will receive lead alerts in your Telegram chat.",
      telegramLinkedAt: "Linked",
      telegramConnected: "Connected",
      telegramUnlink: "Unlink Telegram",
      telegramUnlinking: "Unlinking...",
      telegramNotConfigured: "Telegram notifications are not yet configured for this platform. Contact support for details.",
    },
    notifications: {
      title: "Notifications",
      bell: "Notifications",
      empty: "No notifications yet",
      markAllRead: "Mark all read",
    },
    wizard: {
      title: "Create a bot",
      lead: "A few quick steps — one screen at a time. Your progress saves automatically on this device (Telegram tokens are never stored in the browser).",
      assistiveHint: "Use Continue to move forward and Back to review previous choices.",
      loading: "Loading your saved progress...",
      step: "Step",
      of: "of",
      back: "Back",
      continue: "Continue",
      exitToBots: "Exit to bots",
      skipForNow: "Skip for now",
      createBot: "Create bot",
      creatingBot: "Creating bot...",
      stepNiche: "Niche",
      stepGoal: "Goal",
      stepBasics: "Basics",
      stepChannel: "Channel",
      stepKnowledge: "Knowledge",
      stepReview: "Review",
      nicheTitle: "What is this bot for?",
      nicheDesc: "Pick the context that best matches your business. You can refine details later.",
      goalTitle: "What should the bot achieve?",
      goalDesc: "Choose a primary outcome so tone and flows stay aligned.",
      basicsTitle: "Name and voice",
      basicsDesc: "Give your bot a clear name and how it should sound to visitors.",
      channelTitle: "Where people will talk to you",
      channelDesc: "Website widget goes live without a Telegram token. Telegram (or both) needs a valid BotFather token before the bot can be active.",
      knowledgeTitle: "Ground answers in your content",
      knowledgeDesc: "Upload PDF files and add notes to give your bot trusted business context.",
      reviewTitle: "Review and create",
      reviewDesc: "Confirm your choices. The status we create matches real backend rules.",
      nicheLoading: "Loading supported niches...",
      nicheLegend: "Niche",
      nicheFallback: "Could not refresh niche list from the server. Showing saved defaults — verify your connection and try reloading.",
      goalLegend: "Goal",
      goalSupport: "Support",
      goalSupportHint: "Resolve issues fast with guided troubleshooting and escalation.",
      goalSales: "Sales",
      goalSalesHint: "Convert visitors into leads with qualification and next-step prompts.",
      goalFaq: "FAQ",
      goalFaqHint: "Answer common questions with concise, reliable responses.",
      goalConsulting: "Consulting",
      goalConsultingHint: "Collect context and deliver expert-style recommendations.",
      botName: "Bot name",
      botNameHelp: "Shown in your workspace and future channel settings.",
      botNamePlaceholder: "e.g. Shop Helper",
      toneLegend: "Tone",
      toneHelp: "Tone is optional. You can leave it blank and adjust personality after launch.",
      toneFriendly: "Friendly & concise",
      toneProfessional: "Professional & formal",
      tonePlayful: "Playful & light",
      toneNeutral: "Neutral & factual",
      languageLabel: "Language",
      languageHelp: "This is stored in the draft and will map to multilingual behavior when backend support is ready.",
      shortDesc: "Short description",
      shortDescPlaceholder: "e.g. Helps new customers choose plans and answers billing questions.",
      openingLine: "Opening line",
      openingLineHelp: "Leave empty to use the suggested default for your niche and language.",
      defaultWelcome: "Hi! I can help with orders or product questions.",
      optional: "(optional)",
      channelHint: "Website widget does not require a Telegram token. If you choose Telegram or Both, the backend only marks the bot active after a valid BotFather token and successful webhook registration.",
      channelLegend: "Channel",
      chWebsite: "Website widget",
      chWebsiteHint: "No Telegram token required — bot can be active for the web channel.",
      chTelegram: "Telegram",
      chTelegramHint: "Requires a valid BotFather token before the bot can be active.",
      chBoth: "Both",
      chBothHint: "Web can go active; Telegram still needs a verified token and webhook.",
      proPlus: "Pro+",
      upgradeForTelegram: "Upgrade to Pro or higher to use Telegram.",
      telegramRequiresPro: "Telegram requires a Pro plan or higher.",
      upgradeNow: "Upgrade now",
      telegramToken: "Telegram bot token",
      telegramTokenHelp: "From BotFather. If you skip this, we create the bot as channel pending — not active — until you connect Telegram in the bot settings.",
      telegramTokenPlaceholder: "Paste token to go live on Telegram now",
      channelPending: "channel pending",
      knowledgeHint: "Knowledge gives the bot trusted business context. Upload PDF files directly here — they'll be sent to the server automatically after the bot is created.",
      typicalSources: "Typical sources",
      srcPdf: "PDF documents",
      srcFaq: "FAQ documents",
      srcService: "Service information",
      srcPricing: "Pricing info",
      pdfLiveTitle: "PDFs live on the bot page",
      pdfLiveBody: "After you create this bot, open it from Bots and use Knowledge base there.",
      notesLabel: "Notes",
      notesHelp: "Add URLs or key facts now if you want. Leaving this blank will not block creation.",
      notesPlaceholder: "e.g. Pricing page URL, return policy highlights...",
      uploadDropTitle: "Drop PDF files here or click to browse",
      uploadDropMeta: "PDF only · Max 20 MB per file",
      removeFile: "Remove",
      fileTooLarge: "File is too large (max 20 MB)",
      fileNotPdf: "Only PDF files are accepted",
      pendingUploadNote: "Files will be uploaded automatically after bot creation",
      revFiles: "PDF files",
      noFilesAttached: "No files attached",
      filesReady: "file(s) ready to upload",
      uploadingFiles: "Uploading knowledge files...",
      uploadComplete: "All files uploaded successfully!",
      uploadPartialFail: "Some files failed to upload",
      revNiche: "Niche",
      revGoal: "Goal",
      revName: "Name",
      revLanguage: "Language",
      revTone: "Tone",
      revChannel: "Channel",
      revTelegramToken: "Telegram token",
      revKnowledge: "Knowledge notes",
      tokenNA: "Not applicable",
      tokenProvided: "Provided (validated on the server)",
      tokenNotProvided: "Not provided — expect channel pending",
      knowledgeSkipped: "Skipped",
      knowledgeNone: "None (upload files after creation)",
      expectedStatus: "Expected workspace status",
      outcomeActiveWeb: "Active (web)",
      outcomeActiveWebDetail: "No Telegram token required. The bot can be used from the website widget path once you embed it.",
      outcomeActiveTg: "Active (if Telegram accepts the token)",
      outcomeActiveTgDetail: "We verify the token and register the webhook on the server.",
      outcomePending: "Channel pending",
      outcomePendingDetail: "Saved without a Telegram token. Finish setup from the bot's Telegram panel.",
      outcomeDraft: "Draft",
      outcomeDraftDetail: "Choose a channel to see the outcome.",
      doneActiveTitle: "Bot saved and active",
      doneActiveBody: "Your workspace status matches the server: this bot is active for the channels that are ready.",
      donePendingTitle: "Bot saved — setup incomplete",
      donePendingBody: "Status is channel pending until Telegram is connected with a valid token and webhook.",
      doneDefaultTitle: "Bot saved",
      doneDefaultBody: "Taking you to your bots workspace...",
      serverStatus: "Server status:",
      primaryChannel: "primary channel:",
      openBots: "Open bots",
    },
  },
  superadmin: {
    nav: {
      overview:     "Platform Overview",
      users:        "Users",
      bots:         "Bots",
      billing:      "Billing",
      aiUsage:      "AI Usage",
      auditLog:     "Audit Log",
      featureFlags: "Feature Flags",
      support:      "Support",
      coupons:      "Coupons",
      analytics:    "Segment Analytics",
      abuse:        "Abuse Detection",
      export:       "Data Export",
      campaigns:    "Email Campaigns",
      webhookLogs:  "Webhook Logs",
    },
    common: {
      loading: "Loading...",
      error: "Error",
      save: "Save",
      saving: "Saving...",
      cancel: "Cancel",
      create: "Create",
      edit: "Edit",
      delete: "Delete",
      deleting: "Deleting...",
      confirm: "Confirm",
      total: "Total",
      noRecords: "No records found",
      actions: "Actions",
      status: "Status",
      period: "Period",
      allStatuses: "All statuses",
      allPlans: "All plans",
      allTypes: "All types",
      allActions: "All actions",
      clear: "Clear",
      view: "View",
      back: "Back",
    },
    flags: {
      total: "flags",
      newFlag: "+ New flag",
      key: "Key",
      state: "State",
      plan: "Plan",
      description: "Description",
      updated: "Updated",
      enabled: "Enabled",
      disabled: "Disabled",
      toggleTitle: "Toggle state",
      createTitle: "Create new flag",
      editTitle: "Edit flag",
      keyLabel: "Key *",
      keyHelp: "Lowercase letters, digits and _ only",
      keyPlaceholder: "e.g. advanced_analytics",
      descLabel: "Description (optional)",
      descPlaceholder: "What this flag controls...",
      targetPlan: "Target plan (optional)",
      globalAllPlans: "Global (all plans)",
      enableOnCreate: "Enable now",
      deleteTitle: "Delete flag",
      deleteConfirm: "Delete flag",
      deleteWarn: "This action cannot be undone.",
      yesDelete: "Yes, delete",
      emptyState: "No flags yet. Create a new flag.",
      targetUsers: "Target Users",
      targetUsersHelp: "Enter user emails to enable for specific users",
      addEmail: "Add",
      emailPlaceholder: "user@example.com",
      usersTargeted: "users targeted",
      noUserTarget: "No user targeting",
      invalidEmail: "Invalid email format",
    },
    billing: {
      user: "User",
      plan: "Plan",
      periodStart: "Period start",
      periodEnd: "Period end",
      canceled: "Canceled",
      stripe: "Stripe",
      changePlan: "Change plan",
      changePlanTitle: "Change plan",
      newPlan: "New plan",
      reason: "Reason (optional)",
      reasonPlaceholder: "Admin note...",
      blocked: "Blocked",
      manual: "Manual",
      free: "free",
      statusActive: "Active",
      statusTrialing: "Trial",
      statusPastDue: "Past due",
      statusCanceled: "Canceled",
      statusExpired: "Expired",
      totalActive: "Total Active",
      totalPastDue: "Total Past Due",
      estimatedMrr: "Estimated MRR",
      mrrNote: "Based on current page plan prices",
    },
    aiUsage: {
      periodLabel: "Period:",
      summaryTitle: "platform AI usage",
      totalCalls: "Total calls",
      successful: "Successful",
      failed: "Failed",
      successRate: "Success rate",
      totalTokens: "Total tokens",
      totalCost: "Total cost",
      dailyHistory: "Daily history",
      date: "Date",
      calls: "Calls",
      tokens: "Tokens",
      costUsd: "Cost (USD)",
      topConsumers: "Top token consumers (Top 10)",
      user: "User",
      cost: "Cost",
      noData: "No AI usage data available for this period.",
    },
    auditLog: {
      time: "Time",
      action: "Action",
      entityType: "Type / Entity ID",
      actor: "Actor",
      meta: "Meta",
      snapshot: "Snapshot",
      snapshotTitle: "Snapshot",
      before: "Before",
      after: "After",
      metadata: "Metadata",
      sinceDate: "Since (date)",
    },
    export: {
      intro: "Export platform data as CSV for reporting, auditing, and financial analysis. Downloads include all rows.",
      download: "Download",
      downloading: "Downloading...",
      downloadFailed: "Failed to download",
      usersLabel: "Users",
      usersDesc: "All registered users — ID, email, role, status, timestamps.",
      subscriptionsLabel: "Subscriptions",
      subscriptionsDesc: "All subscriptions — plan, status, Stripe IDs, billing periods.",
      aiUsageLabel: "AI Usage",
      aiUsageDesc: "Daily AI usage aggregates per bot — requests, tokens, cost.",
      couponsLabel: "Coupons",
      couponsDesc: "All coupon codes — discount, usage stats, expiry.",
      quickPresets: "Quick presets",
      preset7d: "Last 7 days",
      preset30d: "Last 30 days",
      preset90d: "Last 90 days",
      presetYtd: "Year to date",
    },
    overview: {
      intro: "Live platform stats. Use the sidebar to inspect users, bots, and billing.",
      loadingOverview: "Loading overview...",
      usersAndBots: "Users & Bots",
      registeredUsers: "Registered users",
      activeUsers: "Active users",
      totalBots: "Total bots",
      activeBots: "Active bots",
      leads: "Leads",
      conversations: "Conversations",
      billingRevenue: "Billing & Revenue",
      mrr: "MRR",
      mrrSub: "Monthly Recurring Revenue",
      paidActive: "Paid active",
      paidActiveSub: "Active paid subscribers",
      freePlan: "Free plan",
      freePlanSub: "On free tier",
      pastDue: "Past due",
      pastDueSub: "Payment failed",
      canceled: "Canceled",
      canceledSub: "Churned",
      planDistribution: "Plan Distribution",
      generatedAt: "Generated at",
      viewBilling: "View billing details",
      planChart: "Plan Distribution",
      autoRefresh: "Auto-refresh",
      refreshEvery: "Refreshing every",
      seconds: "s",
      recentActivity: "Recent Activity",
    },
    users: {
      intro: "All workspace accounts. Open a row for detail and moderation.",
      showingRange: "Showing",
      noUsers: "No users",
      selected: "selected",
      suspend: "Suspend",
      activate: "Activate",
      applyTo: "Apply to",
      previous: "Previous",
      next: "Next",
      selectAll: "Select all",
      email: "Email",
      role: "Role",
      status: "Status",
      bots: "Bots",
      updated: "Updated",
      inactive: "Inactive",
      suspended: "Suspended",
      active: "Active",
      confirmBulkTitle: "Confirm Bulk Action",
      confirmBulkHint: "Apply action to selected users?",
      reasonOptional: "Reason (optional)",
      reasonPlaceholder: "Reason for suspension...",
      processing: "Processing...",
      confirmAction: "Confirm",
      bulkSuccess: "Bulk action complete",
    },
    botsList: {
      intro: "All bots across tenants. Open a row for configuration and moderation.",
      showingRange: "Showing",
      noBots: "No bots",
      previous: "Previous",
      next: "Next",
      bot: "Bot",
      owner: "Owner",
      status: "Status",
      channels: "Channels",
      updated: "Updated",
      platformSuspended: "Platform suspended",
      widget: "Widget",
      telegram: "Telegram",
      selected: "selected",
      bulkSuspend: "Suspend Selected",
      bulkActivate: "Activate Selected",
      bulkSuspendTitle: "Bulk Suspend Bots",
      bulkActivateTitle: "Bulk Activate Bots",
      bulkApplyTo: "This action will apply to",
      botsCount: "bots",
      bulkReason: "Reason (optional)",
      bulkReasonPlaceholder: "e.g. Policy violation, spam content...",
    },
    userDetail: {
      loadingUser: "Loading user...",
      backToUsers: "Back to users",
      inspectTenant: "Inspect tenant (read-only, audited)",
      email: "Email",
      name: "Name",
      role: "Role",
      active: "Active",
      verified: "Verified",
      password: "Password",
      suspendedAt: "Suspended at",
      suspensionNote: "Suspension note",
      oauthProviders: "OAuth providers",
      bots: "Bots",
      created: "Created",
      updated: "Updated",
      yes: "Yes",
      no: "No",
      set: "Set",
      notSet: "Not set",
      activateUser: "Activate user",
      cannotSuspendSelf: "You cannot suspend your own account from this console.",
      suspendUser: "Suspend user",
      impersonation: "Impersonation",
      impersonationDesc: "Generate a 15-minute read-only token to view this user's account. Logged to audit.",
      generating: "Generating...",
      generateToken: "Generate Impersonation Token",
      tokenHint: "Token (valid 15 min) — copy and use as Bearer token:",
      copy: "Copy",
      dismiss: "Dismiss",
      planOverride: "Plan Override",
      plan: "Plan",
      reasonOptional: "Reason (optional)",
      reasonPlaceholder: "Internal reason...",
      applying: "Applying...",
      applyOverride: "Apply Override",
      userSuspended: "User suspended.",
      userActivated: "User activated.",
      planOverridden: "Plan overridden.",
      suspendTitle: "Suspend user",
      suspendDesc: "Sets the account inactive and blocks sign-in. Optional internal note is stored for operators and audit.",
      suspendConfirm: "Suspend",
    },
    botDetail: {
      loadingBot: "Loading bot...",
      backToBots: "Back to bots",
      name: "Name",
      botId: "Bot ID",
      ownerEmail: "Owner email",
      ownerId: "Owner ID",
      niche: "Niche",
      goal: "Goal",
      status: "Status",
      providerModel: "Provider / model",
      widget: "Widget",
      telegram: "Telegram",
      platformSuspended: "Platform suspended",
      suspensionNote: "Platform suspension note",
      welcome: "Welcome",
      tone: "Tone",
      language: "Language",
      description: "Description",
      temperature: "Temperature",
      maxOutputTokens: "Max output tokens",
      created: "Created",
      updated: "Updated",
      configured: "Configured",
      notConfigured: "Not configured",
      connected: "Connected",
      notConnected: "Not connected",
      clearSuspension: "Clear platform suspension",
      platformSuspendBot: "Platform-suspend bot",
      botSuspended: "Bot platform-suspended.",
      suspensionCleared: "Platform suspension cleared.",
      suspendBotTitle: "Platform-suspend bot",
      suspendBotDesc: "Blocks public widget, Telegram AI replies, and dashboard test chat for this bot. Owner workspace is unchanged.",
      suspendBotConfirm: "Suspend bot",
      performance: "Performance",
      conversations: "Conversations",
      leadsGenerated: "Leads Generated",
      aiCalls: "AI Calls",
      aiTokens: "AI Tokens",
    },
    support: {
      loadError: "Failed to load tickets.",
      updateError: "Failed to update ticket.",
      allStatuses: "All statuses",
      statusOpen: "Open",
      statusInProgress: "In Progress",
      statusResolved: "Resolved",
      statusClosed: "Closed",
      allPriorities: "All priorities",
      priorityLow: "Low",
      priorityNormal: "Normal",
      priorityHigh: "High",
      ticketsCount: "tickets",
      subject: "Subject",
      user: "User",
      status: "Status",
      priority: "Priority",
      created: "Created",
      actions: "Actions",
      noTickets: "No tickets found.",
      notePrefix: "Note:",
      edit: "Edit",
      prevPage: "Prev",
      nextPage: "Next",
      pageOf: "Page",
      updateTitle: "Update Ticket",
      statusLabel: "Status",
      priorityLabel: "Priority",
      adminNote: "Admin Note",
      notePlaceholder: "Leave a note for this ticket...",
      replyTitle: "Ticket Details",
      ticketBody: "Message",
      replyLabel: "Admin Reply",
      replyPlaceholder: "Type your reply...",
      replyAndProgress: "Reply & Mark In Progress",
      replyAndResolve: "Reply & Resolve",
      submittedAt: "Submitted",
      resolvedAt: "Resolved",
      noReplyYet: "No reply yet",
      previousReply: "Previous Reply",
      cancel: "Cancel",
      saving: "Saving...",
      save: "Save",
    },
    abuse: {
      loadError: "Failed to load abuse report.",
      suspendError: "Suspend failed.",
      periodLabel: "Period (days):",
      day1: "1 day",
      day3: "3 days",
      day7: "7 days",
      minCalls: "Min calls:",
      refresh: "Refresh",
      highUsageTitle: "High-Usage Accounts",
      user: "User",
      calls: "Calls",
      failed: "Failed",
      tokens: "Tokens",
      cost: "Cost",
      errorRate: "Error rate",
      actions: "Actions",
      noHighUsage: "No high-usage accounts detected.",
      suspend: "Suspend",
      topErrorsTitle: "Top Error Codes",
      errorCode: "Error Code",
      occurrences: "Occurrences",
      noErrors: "No error data.",
      suspendedUser: "Suspended",
      failedToSuspend: "Failed to suspend",
    },
    campaigns: {
      segmentAllUsers: "All Active Users",
      segmentPastDue: "Past Due",
      segmentFreePlan: "Free Plan",
      segmentPaidUsers: "Paid Users",
      segmentInactive7d: "Inactive 7+ Days",
      loadError: "Failed to load campaigns.",
      createError: "Failed to create campaign.",
      updateError: "Failed to update campaign.",
      sendError: "Failed to send campaign.",
      deleteError: "Failed to delete campaign.",
      newCampaign: "+ New Campaign",
      campaignsCount: "campaigns",
      subject: "Subject",
      segment: "Segment",
      status: "Status",
      sentFailed: "Sent / Failed",
      sentAt: "Sent at",
      actions: "Actions",
      noCampaigns: "No campaigns yet.",
      recipients: "recipients",
      failedCount: "failed",
      preview: "Preview",
      edit: "Edit",
      send: "Send",
      delete: "Delete",
      prevPage: "Prev",
      nextPage: "Next",
      pageOf: "Page",
      newTitle: "New Email Campaign",
      subjectLabel: "Subject",
      targetSegment: "Target Segment",
      bodyLabel: "Body (HTML)",
      cancel: "Cancel",
      creating: "Creating...",
      createDraft: "Create Draft",
      editTitle: "Edit Campaign",
      bodyHtml: "Body HTML",
      saving: "Saving...",
      saveChanges: "Save Changes",
      previewTitle: "Preview",
      segmentLabel: "Segment",
      close: "Close",
      sendTitle: "Send Campaign?",
      sendConfirm: "This will immediately send the campaign. This action cannot be undone.",
      sending: "Sending...",
      confirmSend: "Confirm Send",
      deleteTitle: "Delete Campaign?",
      deleteConfirm: "Are you sure? This cannot be undone.",
      deleting: "Deleting...",
      campaignCreated: "Campaign created",
      campaignUpdated: "Campaign updated.",
      campaignSending: "Campaign is sending",
      templateLabel: "Template",
      tplBlank: "Blank",
      tplBlankDesc: "Start from scratch",
      tplWelcome: "Welcome",
      tplWelcomeDesc: "Onboarding email for new users",
      tplAnnouncement: "Announcement",
      tplAnnouncementDesc: "Product update or news",
      tplPromotion: "Promotion",
      tplPromotionDesc: "Discount or special offer",
      tplReengagement: "Re-engagement",
      tplReengagementDesc: "Win back inactive users",
    },
    coupons: {
      loadError: "Failed to load coupons.",
      createError: "Failed to create coupon.",
      updateError: "Failed to update coupon.",
      deleteError: "Failed to delete coupon.",
      codeExists: "Coupon code already exists.",
      newCoupon: "+ New Coupon",
      couponsCount: "coupons",
      code: "Code",
      discount: "Discount",
      plan: "Plan",
      uses: "Uses",
      expires: "Expires",
      status: "Status",
      actions: "Actions",
      noCoupons: "No coupons yet.",
      allPlans: "all",
      active: "active",
      inactive: "inactive",
      edit: "Edit",
      delete: "Delete",
      createTitle: "Create Coupon",
      codeLabel: "Code (uppercase, e.g. LAUNCH50)",
      typeLabel: "Type",
      valueLabel: "Value",
      percentType: "Percent (%)",
      usdType: "USD ($)",
      targetPlan: "Target Plan (optional)",
      maxUses: "Max Uses (optional)",
      expiresAt: "Expires At (optional)",
      cancel: "Cancel",
      creating: "Creating...",
      create: "Create",
      editTitle: "Edit",
      activeLabel: "Active",
      inactiveLabel: "Inactive",
      clearExpiry: "Clear expiry (never expire)",
      saving: "Saving...",
      save: "Save",
      deleteTitle: "Delete Coupon?",
      deleteConfirm: "Are you sure you want to permanently delete this coupon? This cannot be undone.",
      deleting: "Deleting...",
      couponCreated: "Coupon created.",
      analyticsActive: "Active Coupons",
      analyticsRedemptions: "Total Redemptions",
      analyticsExpired: "Expired",
      analyticsMaxedOut: "Maxed Out",
      analyticsAvgDiscount: "Avg. Discount",
    },
    webhooks: {
      loadError: "Failed to load webhook logs.",
      failedTotal: "failed webhooks total",
      showFailedOnly: "Show failed only",
      allSources: "All sources",
      stripe: "Stripe",
      telegram: "Telegram",
      allStatuses: "All statuses",
      received: "Received",
      processed: "Processed",
      failed: "Failed",
      clearDates: "Clear dates",
      logsCount: "logs",
      source: "Source",
      eventType: "Event Type",
      status: "Status",
      bot: "Bot",
      receivedAt: "Received",
      details: "Details",
      noLogs: "No webhook logs found.",
      view: "View",
      prevPage: "Prev",
      nextPage: "Next",
      pageOf: "Page",
      close: "Close",
    },
    tenant: {
      loadingInspection: "Loading inspection...",
      backToUser: "Back to user",
      intro: "Read-only operational snapshot. Opening this page triggers an audited superadmin inspection event.",
      leads: "Leads",
      conversations: "Conversations",
      aiCalls: "AI calls (window)",
      aiFailures: "AI failures (window)",
      tokensWindow: "Tokens (window)",
      tenantSummary: "Tenant summary",
      email: "Email",
      role: "Role",
      active: "Active",
      botsProfile: "Bots (profile)",
      yes: "Yes",
      no: "No",
      channelMix: "Channel mix (conversations)",
      noConversations: "No conversations yet.",
      channel: "Channel",
      botsShown: "Bots",
      noBotsForTenant: "No bots for this tenant.",
      bot: "Bot",
      status: "Status",
      channels: "Channels",
      widget: "Widget",
      telegram: "Telegram",
      aiUsageWindow: "AI usage window",
      dailyRollup: "Daily AI rollup (recent days)",
      noDailyData: "No daily aggregates in range.",
      date: "Date",
      requests: "Requests",
      tokens: "Tokens",
      costUsd: "Cost (USD)",
      recentErrors: "Recent AI errors",
      noFailedCalls: "No failed AI calls on record for this tenant.",
      when: "When",
      model: "Model",
      code: "Code",
    },
    analytics: {
      channelWebWidget: "Web Widget",
      channelTelegram: "Telegram",
      channelAdminTest: "Admin Test",
      loadError: "Failed to load analytics.",
      periodLabel: "Period: last",
      channelDistribution: "Channel Distribution",
      noConversationData: "No conversation data yet.",
      userSignups: "User Signups",
      noSignupData: "No signup data for this period.",
      date: "Date",
      newUsers: "New Users",
      bar: "Bar",
      planSegments: "Plan Segments",
      plan: "Plan",
      status: "Status",
      count: "Count",
      churnByPlan: "Churn by Plan",
      canceled: "Canceled",
      noChurnData: "No churn data.",
      botsByNiche: "Bots by Niche",
      niche: "Niche",
      bots: "Bots",
      noData: "No data.",
      botsByGoal: "Bots by Goal Type",
      goal: "Goal",
      signupChart: "Signup Trend",
      channelChart: "Channel Distribution",
    },
    moderation: {
      internalNote: "Internal note (optional)",
      internalNotePlaceholder: "Internal note (optional, max 1024 chars)",
      cancel: "Cancel",
    },
  },
  common: {
    loading: "Loading...",
    error: "Something went wrong",
    save: "Save",
    cancel: "Cancel",
    delete: "Delete",
    edit: "Edit",
    back: "Back",
    next: "Next",
    finish: "Finish",
    optional: "optional",
    or: "or",
  },
};

const uz: Translations = {
  nav: {
    features: "Imkoniyatlar",
    pricing: "Narxlar",
    faq: "Savol-javob",
    login: "Kirish",
    getStarted: "Boshlash",
    dashboard: "Boshqaruv paneli",
    logout: "Chiqish",
    language: "Til",
  },
  hero: {
    badge: "AI Lídlar Generatsiyasi Platformasi",
    headline: "Tashrif buyuruvchilarni",
    headlineAccent: "Haqiqiy Mijozlarga",
    subtext:
      "Tashrif buyuruvchilar bilan gaplashadigan, ularning ehtiyojlarini aniqlaydigan va leads sifatida taqdim etadigan aqlli AI bot yarating — veb-saytingizda yoki Telegramda. Kod talab etilmaydi.",
    cta: "Botingizni Yarating — Bepul",
    ctaSecondary: "Qanday Ishlashini Ko'rish",
    trustedBy: "Jahon bo'ylab bizneslar ishonadi",
  },
  stats: {
    bots: "500+",
    botsLabel: "Faol Botlar",
    leads: "10K+",
    leadsLabel: "Generatsiya qilingan Lidlar",
    uptime: "99.9%",
    uptimeLabel: "Ish vaqti",
  },
  howItWorks: {
    title: "Qanday Ishlaydi",
    subtitle: "Ro'yxatdan o'tishdan birinchi lídgacha bir necha daqiqada.",
    steps: [
      { title: "Ro'yxatdan o'ting", desc: "Bir necha soniyada bepul akkaunt yarating." },
      {
        title: "Nishangizni Tanlang",
        desc: "Botga nima sotishingiz va kimga yordam berishingizni ayting.",
      },
      {
        title: "Bilimlarni Yuklang",
        desc: "Javoblar sizga o'xshash eshitilishi uchun PDF yoki eslatmalar qo'shing.",
      },
      {
        title: "Kanal Ulang",
        desc: "Saytingizga vidjet qo'shing yoki Telegram kanalingizni ulang.",
      },
      {
        title: "Lidlarni Oling",
        desc: "Tashrif buyuruvchilar suhbatlashadi, siz kuzatish uchun toza lidlar olasiz.",
      },
    ],
  },
  features: {
    title: "Barcha Imkoniyatlar",
    subtitle: "AI yordamchingiz mijozlar bilan suhbatlashadi va tayyor lidlarni sizga yetkazadi.",
    items: [
      {
        title: "Avtomatik Lid Yig'ish",
        desc: "Bot suhbat davomida mijozning ismi, telefoni va emailini oladi — lidlar to'g'ridan-to'g'ri panelingizga tushadi.",
      },
      {
        title: "Bilim Bazasidan Javoblar",
        desc: "Hujjatlaringizni yuklang va bot mijozlarga sizning mahsulot va xizmatlaringiz haqida aniq javob beradi.",
      },
      {
        title: "Sayt va Telegramda Ishlaydi",
        desc: "Saytingizga chat vidjet o'rnating yoki Telegram bot ulang — barchasini bitta joydan boshqaring.",
      },
      {
        title: "Bir Necha Daqiqada Ishga Tushiring",
        desc: "Biznes turingizni tanlang, uslubni sozlang va botingiz tayyor — dasturchi kerak emas.",
      },
    ],
  },
  niches: {
    title: "Sizning Nishaniz Uchun",
    subtitle: "Boshlash nuqtasini tanlang — ohang va oqimlar sizning ish uslubingizga mos.",
    loading: "Yuklanmoqda...",
  },
  pricing: {
    title: "Oddiy, Shaffof Narxlar",
    subtitle: "Bepul boshlang. O'sganda yangilang.",
    perMonth: "/ oy",
    popular: "Eng Mashhur",
    free: "Bepul",
    plans: {
      free: {
        name: "Bepul",
        price: "0",
        desc: "Phoenix AI ni majburiyatsiz sinab ko'ring",
        cta: "Bepul Boshlash",
        features: [
          "1 bot",
          "100 suhbat/oy",
          "Sayt vidjeti",
          "1 PDF hujjat",
          "Phoenix AI branding",
          "Jamiyat yordami",
        ],
      },
      pro: {
        name: "Pro",
        price: "39",
        desc: "Lidlarni keng miqyosda yig'ishga tayyor bizneslar uchun",
        cta: "Pro Olish",
        features: [
          "5 bot",
          "5,000 suhbat/oy",
          "Sayt + Telegram",
          "25 PDF hujjat",
          "Branding olib tashlash",
          "Tahlillar paneli",
          "Email yordam",
        ],
      },
      business: {
        name: "Biznes",
        price: "99",
        desc: "To'liq imkoniyat va moslashuvchanlik kerak bo'lgan jamoalar uchun",
        cta: "Biznes Olish",
        features: [
          "Cheksiz botlar",
          "20,000 suhbat/oy",
          "Barcha kanallar",
          "Cheksiz hujjatlar",
          "API kirish",
          "5 jamoa a'zosi",
          "Kengaytirilgan tahlillar",
          "Ustuvor yordam",
        ],
      },
      enterprise: {
        name: "Korporativ",
        price: "Bog'laning",
        desc: "Maxsus hajm, SLA va shaxsiy yordam",
        cta: "Bog'lanish",
        features: [
          "Biznesdagi barcha imkoniyatlar",
          "Cheksiz suhbatlar",
          "Maxsus SLA",
          "Shaxsiy hisob menejeri",
          "Maxsus integratsiyalar",
          "On-premise variant",
        ],
      },
    },
  },
  faq: {
    title: "Ko'p Beriladigan Savollar",
    subtitle: "Mijozlarimiz eng ko'p so'raydigan savollarga javoblar.",
    items: [
      {
        q: "Bot mijozlarimga qanday javob berishini qayerdan biladi?",
        a: "Siz hujjatlaringizni (narxlar, xizmatlar, FAQ) yuklaysiz va bot ulardan o'rganadi. Bot faqat sizning haqiqiy ma'lumotlaringiz asosida javob beradi.",
      },
      {
        q: "Bot javob bera olmasa nima bo'ladi?",
        a: "Bot mijozga savolini haqiqiy xodimga uzatishini aytadi va suhbat panelingizda belgilanadi — siz keyinroq bog'lanishingiz mumkin.",
      },
      {
        q: "Bot yig'gan suhbatlar va lidlarni ko'ra olamanmi?",
        a: "Ha. Har bir suhbat, yig'ilgan kontakt va lid panelda real vaqtda ko'rinadi. Filtrlash, eksport qilish va kuzatish mumkin.",
      },
      {
        q: "Botni saytimga qanday o'rnataman?",
        a: "Bitta qator kodni nusxalab saytingizga qo'yasiz. WordPress, Tilda, Wix yoki oddiy HTML — barchasi bilan ishlaydi. 2 daqiqada tayyor.",
      },
      {
        q: "Bot bir nechta tilda ishlaydimi?",
        a: "Ha. Bot mijozning tilini avtomatik aniqlaydi va o'sha tilda javob beradi. Ingliz, rus, o'zbek, turk, arab va boshqa ko'plab tillarni qo'llab-quvvatlaydi.",
      },
      {
        q: "To'lamasdan sinab ko'rsa bo'ladimi?",
        a: "Albatta. Bepul rejada 1 bot va oyiga 100 suhbat bor — bank kartasi talab qilinmaydi. Ko'proq kerak bo'lganda yangilaysiz.",
      },
      {
        q: "Mijozlarimning ma'lumotlari xavfsizmi?",
        a: "Barcha ma'lumotlar shifrlangan holda saqlanadi va uzatiladi. Biz ma'lumotlaringizni sotmaymiz va AI o'qitish uchun ishlatmaymiz. Istalgan vaqtda o'chirishingiz mumkin.",
      },
    ],
  },
  cta: {
    title: "Ko'proq lid olishga tayyormisiz?",
    subtitle: "Yuzlab bizneslar allaqachon Phoenix AI dan foydalanmoqda.",
    button: "Bepul Akkaunt Yaratish",
  },
  footer: {
    tagline: "Tashrif buyuruvchilarni haqiqiy mijozlarga aylantiruvchi AI chatbotlar.",
    rights: "Barcha huquqlar himoyalangan.",
    contact: "Aloqa",
    terms: "Shartlar",
    privacy: "Maxfiylik",
    product: "Mahsulot",
    legal: "Huquqiy",
  },
  auth: {
    login: {
      title: "Xush kelibsiz",
      subtitle: "Phoenix AI ish maydoningizga kiring.",
      email: "Elektron pochta",
      password: "Parol",
      submit: "Kirish",
      submitting: "Kirilmoqda...",
      forgotPassword: "Parolni unutdingizmi?",
      noAccount: "Akkountingiz yo'qmi?",
      createOne: "Yarating",
    },
    signup: {
      title: "Akkaunt Yaratish",
      subtitle: "Phoenix AI bilan qurilishni boshlang.",
      name: "To'liq Ism",
      nameOptional: "(ixtiyoriy)",
      email: "Elektron pochta",
      password: "Parol",
      confirmPassword: "Parolni Tasdiqlash",
      submit: "Akkaunt Yaratish",
      submitting: "Akkaunt yaratilmoqda...",
      haveAccount: "Akkountingiz bormi?",
      signIn: "Kiring",
    },
    forgotPassword: {
      title: "Parolni Tiklash",
      subtitle: "Elektron pochtangizni kiriting, tiklash havolasini yuboramiz.",
      email: "Elektron pochta",
      submit: "Tiklash Havolasini Yuborish",
      submitting: "Yuborilmoqda...",
      success:
        "Kirish qutingizni tekshiring — agar bu elektron pochta ro'yxatdan o'tgan bo'lsa, tiklash havolasini yubordik.",
      backToLogin: "Kirishga qaytish",
    },
    resetPassword: {
      title: "Yangi Parol O'rnatish",
      subtitle: "Akkauntingiz uchun kuchli parol tanlang.",
      password: "Yangi Parol",
      confirmPassword: "Yangi Parolni Tasdiqlash",
      submit: "Parolni Tiklash",
      submitting: "Tiklanmoqda...",
      success: "Parol yangilandi! Endi kirishingiz mumkin.",
    },
    verify: {
      title: "Elektron Pochtangizni Tasdiqlang",
      subtitle: "Tasdiqlash havolasi uchun kirish qutingizni tekshiring.",
      success: "Elektron pochta tasdiqlandi! Yo'naltirilmoqda...",
      invalid: "Bu tasdiqlash havolasi yaroqsiz yoki muddati o'tgan.",
      resend: "Tasdiqlash emailini qayta yuborish",
    },
    oauth: {
      google: "Google orqali davom etish",
      github: "GitHub orqali davom etish",
      working: "Kirish yakunlanmoqda...",
    },
    showPassword: "Parolni ko'rsatish",
    hidePassword: "Parolni yashirish",
  },
  dashboard: {
    nav: {
      overview: "Umumiy ko'rinish",
      businessPlan: "Biznes-reja",
      bots: "Botlar",
      leads: "Lidlar",
      knowledge: "Bilimlar bazasi",
      channels: "Kanallar",
      analytics: "Tahlillar",
      billing: "To'lov",
      settings: "Sozlamalar",
      marketingSite: "← Marketing sayti",
    },
    topbar: {
      profile: "Profil",
      settings: "Sozlamalar",
      billing: "To'lov",
      logout: "Chiqish",
    },
    overview: {
      title: "Boshqaruv paneli",
      subtitle: "Ish maydoni ko'rinishi",
      hi: "Salom",
      hiAnon: "Xush kelibsiz",
      welcomeLead: "Bu sizning ish maydoningiz. Bot yarating, bilimlar yuklang va kanal ulang — lidlar yig'ishni boshlang.",
      suggestedSteps: "Boshlash uchun",
      step1: "Birinchi botingizni yarating va uning uslubini sozlang.",
      step2: "Hujjatlar yuklang — bot aniq javob bersin.",
      step3: "Sayt vidjeti yoki Telegram ulang va ishga tushiring.",
      quickActions: "Tezkor harakatlar",
      createBot: "Bot yaratish",
      createBotHint: "Ohang, promptlar va xatti-harakatni sozlang.",
      uploadKnowledge: "Bilim yuklash",
      uploadKnowledgeHint: "Bot uchun PDF, eslatmalar yoki FAQ qo'shing.",
      connectChannel: "Kanal ulash",
      connectChannelHint: "Sayt vidjeti, Telegram yoki boshqa integratsiyalar.",
      activity: "Faoliyatingiz",
      open: "Hammasini ko'rish",
      recentBots: "So'nggi botlar",
      recentBotsEmpty: "Hali botlar yo'q",
      recentBotsEmptyHint: "Birinchi botingizni yarating — bu yerda ko'rinadi.",
      recentLeads: "So'nggi lidlar",
      recentLeadsEmpty: "Hali lidlar yo'q",
      recentLeadsEmptyHint: "Tashrif buyuruvchilar bot bilan suhbatlashganda lidlar bu yerda paydo bo'ladi.",
      channelStatus: "Kanallar",
      channelStatusEmpty: "Kanallar ulanmagan",
      channelStatusEmptyHint: "Sayt vidjeti yoki Telegram ulang — xabarlar qabul qilishni boshlang.",
      createFirst: "Birinchi botingizni yarating",
      createFirstBody: "Hali botlaringiz yo'q. Boshlash bir daqiqa oladi.",
      createFirstBtn: "Bot yaratish",
    },
    leads: {
      title: "Lidlar",
      subtitle: "Botlaringiz orqali yig'ilgan potensial mijozlar — bosqich, harorat va kontaktlarni ko'ring.",
      count: "lid",
      countOne: "lid",
      filtered: "(filtrlangan)",
      showing: "Ko'rsatilmoqda",
      pipelineStatus: "Bosqich holati",
      allStages: "Barcha bosqichlar",
      stNew: "Yangi",
      stContacted: "Bog'lanilgan",
      stQualified: "Malakali",
      stProposal: "Taklif",
      stWon: "Yutilgan",
      stLost: "Yo'qotilgan",
      temperature: "Harorat",
      anyTemp: "Barcha harorat",
      tempCold: "Sovuq",
      tempWarm: "Iliq",
      tempHot: "Issiq",
      nicheId: "Nicha",
      nichePlaceholder: "masalan: ta'lim",
      toolbarHint: "Filterlar API ga real vaqtda so'rov yuboradi.",
      colLead: "Lid",
      colStatus: "Holat",
      colTemp: "Harorat",
      colScore: "Ball",
      colNiche: "Nicha",
      colPhone: "Telefon",
      colCreated: "Yaratilgan",
      loadMore: "Ko'proq yuklash",
      loadingMore: "Yuklanmoqda...",
      emptyTitle: "Hali lidlar yo'q",
      emptyBody: "Tashrif buyuruvchilar botlaringiz bilan suhbatlashganda, malakali lidlar bu yerda paydo bo'ladi.",
      emptyCta: "Botlarga o'tish",
      emptyFilterTitle: "Filtrlarga mos lidlar yo'q",
      emptyFilterBody: "Ko'proq natijalar ko'rish uchun bosqich, harorat yoki nichani tozalang.",
      emptyApiTitle: "Lidlar API mavjud emas",
      emptyApiBody: "Backend ishga tushirilganda, yig'ilgan lidlaringiz bu yerda avtomatik ko'rinadi.",
      retry: "Qayta urinish",
      statsTotal: "Jami",
      statsNew: "Yangi",
      statsQualified: "Malakali",
      statsWon: "Yutilgan",
      statsLost: "Yo'qotilgan",
      statsCold: "Sovuq",
      statsWarm: "Iliq",
      statsHot: "Issiq",
      detailBack: "Lidlar",
      detailSummary: "Xulosa",
      detailSummaryEmpty: "Bu lid uchun xulosa yig'ilmagan.",
      detailCollected: "Yig'ilgan ma'lumotlar",
      detailCollectedEmpty: "Strukturalangan maydonlar saqlanmagan.",
      detailDetails: "Tafsilotlar",
      detailCurrentStatus: "Joriy holat",
      detailPhone: "Telefon",
      detailSource: "Manba",
      detailCreated: "Yaratilgan",
      detailUpdated: "Yangilangan",
      detailPipeline: "Voronka va eslatmalar",
      detailPipelineHint: "Yutilgan va yo'qotilgan yakuniy — faqat harorat va eslatmalarni o'zgartirish mumkin.",
      detailNoTemp: "Harorat belgilanmagan",
      detailNotes: "Ichki eslatmalar",
      detailNotesPlaceholder: "Qo'ng'iroq natijalari, keyingi qadamlar...",
      detailAssignee: "Mas'ul ID (UUID)",
      detailSaving: "Saqlanmoqda...",
      detailSave: "O'zgarishlarni saqlash",
      detailLoadError: "Bu lidni yuklab bo'lmadi.",
      detailLoading: "Lid yuklanmoqda...",
    },
    botDetail: {
      tabSettings: "Sozlamalar va suhbat",
      tabKnowledge: "Bilimlar bazasi",
      tabWidget: "Veb-vidjet",
      tabTelegram: "Telegram",
      subtitle: "Bot tafsilotlari, bilimlar bazasi va test suhbati",
      backToBots: "Botlarga qaytish",
      loadingBot: "Bot tafsilotlari yuklanmoqda...",
      loadError: "Bot tafsilotlarini yuklab bo'lmadi.",
      retry: "Qayta urinish",
      niche: "Nisha",
      goal: "Maqsad",
      currentStatus: "Joriy holat",
      lastUpdated: "Oxirgi yangilanish",
      name: "Nomi",
      status: "Holat",
      tone: "Ohang",
      language: "Til",
      welcomeMessage: "Salomlashish xabari",
      shortDescription: "Qisqa tavsif",
      statusDraft: "Qoralama",
      statusActive: "Faol",
      statusPaused: "To'xtatilgan",
      statusArchived: "Arxivlangan",
      tonePlaceholder: "Do'stona va lo'nda",
      languagePlaceholder: "uz",
      welcomePlaceholder: "Salom! Bugun sizga qanday yordam bera olaman?",
      shortDescPlaceholder: "Bu bot nima bilan shug'ullanishini yozing.",
      modelPlaceholder: "Standart uchun bo'sh qoldiring",
      defaultPlaceholder: "Standart",
      aiResponseTitle: "AI javobi",
      aiResponseHint: "Yaratiladigan javoblar uchun ixtiyoriy sozlash. Standart qiymatlar uchun maydonlarni bo'sh qoldiring.",
      inferenceProvider: "Inference provayderi",
      inferenceProviderHint: "Bu ish maydoni uchun platforma tomonidan boshqariladi.",
      model: "Model",
      modelHint: "Provayderga xos model identifikatori (harflar, raqamlar, nuqta, pastki chiziq, defis).",
      temperature: "Temperatura",
      temperatureHint: "0 = aniqroq, 2 = xilma-xilroq. Bo'sh = provayder standarti.",
      maxTokens: "Maksimal chiqish tokenlari",
      maxTokensHint: "Javob uzunligini cheklaydi. Bo'sh = provayder standarti.",
      temperatureInvalid: "Temperatura 0 va 2 oralig'idagi son bo'lishi yoki standart uchun bo'sh bo'lishi kerak.",
      maxTokensInvalid: "Maksimal chiqish tokenlari 1 dan 8192 gacha butun son bo'lishi yoki standart uchun bo'sh bo'lishi kerak.",
      archiveConfirmText: "Bu bot arxivlansinmi? U botlar ro'yxatingizda arxivlangan holatda ko'rinib turadi.",
      archiving: "Arxivlanmoqda...",
      confirmArchive: "Arxivlashni tasdiqlash",
      cancel: "Bekor qilish",
      saving: "Saqlanmoqda...",
      saveChanges: "O'zgarishlarni saqlash",
      alreadyArchived: "Allaqachon arxivlangan",
      archiveBot: "Botni arxivlash",
      deletePermanently: "Butunlay o'chirish",
      deleteConfirmText: "Bu bot butunlay o'chirilsinmi? Bu amalni qaytarib bo'lmaydi. Barcha bog'liq ma'lumotlar (bilimlar bazasi, suhbatlar, lidlar) o'chiriladi.",
      deleting: "O'chirilmoqda...",
      confirmDelete: "O'chirishni tasdiqlash",
      testChatArchived: "Bot arxivlangan ekan, test suhbati mavjud emas.",
    },
    botTelegram: {
      lead: "Mijozlar bu bot bilan Telegram orqali suhbatlashsin. Xabarlar dashboard test suhbati va veb-vidjet bilan bir xil AI sozlamalaridan foydalanadi.",
      loading: "Telegram sozlamalari yuklanmoqda…",
      loadError: "Telegram sozlamalarini yuklab bo'lmadi.",
      retry: "Qayta urinish",
      upgradeTitle: "Telegram integratsiyasi Pro yoki undan yuqori tarifni talab qiladi.",
      upgradeDesc: "Botingizni Telegram'ga ulash va mijozlarga ularning sevimli messenjerida yetib borish uchun tarifingizni yangilang.",
      upgradeBtn: "Tarifni yangilash",
      botfatherTitle: "BotFather token",
      botfatherIntro: " — Telegram'da oching: ",
      botfatherRun: ", ishga tushiring ",
      botfatherSelect: " yoki botingizni tanlang, so'ng nusxalang: ",
      apiToken: "API token",
      botfatherFormat: " (format ",
      botfatherPaste: "). Uni quyiga bir marta joylashtiring; biz uni Telegram bilan tekshiramiz, shifrlaymiz va ",
      neverShow: "boshqa hech qachon ko'rsatmaymiz",
      botfatherEnd: " bu interfeysda.",
      connectionTitle: "Ulanish",
      pillActive: "Faol",
      pillValidationFailed: "Tekshiruv muvaffaqiyatsiz",
      pillSetupInProgress: "Sozlash davom etmoqda",
      pillNotStarted: "Boshlanmagan",
      webhookRegistered: "Webhook ro'yxatdan o'tgan",
      botUsernamePrefix: "Bot foydalanuvchi nomi: ",
      usernameAfterConfirm: "Telegram botingizni tasdiqlagach, foydalanuvchi nomi shu yerda paydo bo'ladi.",
      usernameConnect: "Botingizning Telegram foydalanuvchi nomini ko'rish uchun ulang.",
      lastVerifiedPrefix: "Oxirgi tekshirilgan: ",
      archivedNotice: "Bu bot arxivlangan. Ulanish va token amallari o'chirilgan. Saqlangan ma'lumotlarni o'chirish uchun uzish hali ham mavjud.",
      lastIssuePrefix: "Oxirgi muammo: ",
      botTokenLabel: "Bot token",
      botTokenHint: "Bir martalik kiritish. Muvaffaqiyatli ulangach, maydonni o'zingiz tozalang yoki biz muvaffaqiyatda tozalaymiz — API maxfiy kalitni qaytarmaydi.",
      tokenPlaceholderStored: "Token saqlangan — almashtirish uchungina joylashtiring (qayta ulang)",
      tokenPlaceholderEmpty: "BotFather'dan tokenni joylashtiring",
      connecting: "Ulanmoqda…",
      updateConnection: "Ulanishni yangilash",
      connectTelegram: "Telegram'ni ulash",
      disconnecting: "Uzilmoqda…",
      disconnect: "Uzish",
    },
    botWidget: {
      lead: "Chat vidjetini saytingizga qo'shing. Sozlamalar ommaviy embed'ga taalluqli; maxfiy kalitlaringiz serverda qoladi.",
      loading: "Vidjet sozlamalari yuklanmoqda…",
      loadError: "Vidjet sozlamalarini yuklab bo'lmadi.",
      retry: "Qayta urinish",
      settingsTitle: "Vidjet sozlamalari",
      settingsHint: "Ruxsat etilgan domenlar qaysi saytlar bu vidjetni yuklashi mumkinligini cheklaydi. Sinov vaqtida har qanday manbaga ruxsat berish uchun bo'sh qoldiring—ishlab chiqarishdan oldin cheklang.",
      enabledTitle: "Vidjet yoqilgan",
      enabledMeta: "O'chirilganda, tashrif buyuruvchilar vidjetni yuklay yoki suhbatlasha olmaydi.",
      allowedDomains: "Ruxsat etilgan domenlar",
      domainsHint: "Har bir qatorda bitta host nomi. Portlar qo'llab-quvvatlanmaydi—faqat hostdan foydalaning.",
      welcomeLabel: "Vidjet salomlashish matni",
      welcomePlaceholder: "Chat ochilganda ko'rsatiladi. Bot standartiga tayanish uchun bo'sh qoldiring.",
      themeLabel: "Mavzu",
      themeAuto: "Avto (tashrif buyuruvchidan)",
      themeLight: "Yorug'",
      themeDark: "Qorong'i",
      themeHint: "Vidjet ko'rinishini boshqaradi; embed buni keyingi yuklanishda hisobga oladi.",
      saving: "Saqlanmoqda…",
      saveBtn: "Vidjet sozlamalarini saqlash",
      installTitle: "O'rnatish",
      installHint: "Ommaviy vidjet kalitingizni HTML'ga joylashtirish xavfsiz. U faqat siz tasdiqlagan domenlarda suhbatga ruxsat beradi.",
      publicKeyLabel: "Ommaviy vidjet kaliti",
      checklistBuild: "Vidjet to'plamini Phoenix AI embed paketidan yarating",
      checklistHost: "Bu faylni CDN yoki statik serveringizda joylashtiring",
      checklistHostSetPre: " va ",
      checklistHostSetPost: " ni ushbu ilovada o'rnating, shunda quyidagi snippet sizning URL'ingizdan foydalanadi.",
      checklistHostConfigured: " (skript URL bu dashboard uchun sozlangan).",
      checklistApiPre: "Ushbu dashboard uchun ",
      checklistApiMid: " ni o'rnating, shunda snippet haqiqiy API manzilingizni o'z ichiga oladi (yoki ",
      checklistApiPost: " ni qo'lda almashtiring).",
      embedSnippet: "Embed snippet",
      copySnippet: "Snippetni nusxalash",
      copied: "Vaqtinchalik xotiraga nusxalandi.",
      copyError: "Nusxalab bo'lmadi—kodni tanlang yoki brauzer ruxsatlarini tekshiring.",
    },
    bots: {
      title: "Sizning botlaringiz",
      subtitle: "Mijozlaringiz uchun botlar yarating va sozlang.",
      createBtn: "Bot yaratish",
      search: "Qidirish",
      searchPlaceholder: "Bot nomini qidirish...",
      status: "Holat",
      allStatuses: "Barcha holatlar",
      statusDraft: "Qoralama",
      statusActive: "Faol",
      statusPaused: "To'xtatilgan",
      statusArchived: "Arxivlangan",
      statusChannelPending: "Kanal kutilmoqda",
      toolbarHint: "Nom, soha yoki maqsad bo'yicha qidiring. Holat bo'yicha filtrlang.",
      colName: "Nomi",
      colNiche: "Nicha",
      colGoal: "Maqsad",
      colStatus: "Holat",
      colUpdated: "Yangilangan",
      colActions: "Amallar",
      clone: "Nusxalash",
      cloning: "Nusxalanmoqda...",
      emptyTitle: "Hali botlar yo'q",
      emptyBody: "Birinchi botingizni yarating — ohang va promptlarni sozlang, bilim qo'shing, kanal ulang.",
      emptyApiNote: "Botlar API ga ulanib bo'lmadi. Siz hali ham yangi bot yaratishingiz mumkin.",
      emptyCta: "Birinchi botingizni yarating",
      retry: "Qayta urinish",
      loading: "Botlar yuklanmoqda...",
    },
    analytics: {
      title: "Tahlillar",
      subtitle: "Botlar, lidlar va sarfingizni bir qarashda kuzating",
      period: "Davr",
      periodDays: "k",
      loading: "Tahlillar yuklanmoqda…",
      noData: "Ma'lumotlar mavjud emas",
      loadError: "Tahlillarni yuklashda xatolik",
      totalBots: "Jami botlar",
      activeCount: "faol",
      totalLeads: "Jami lidlar",
      lastDays: "oxirgi",
      hotLeads: "Issiq lidlar",
      highIntent: "yuqori niyat",
      wonLeads: "Yutuqli lidlar",
      convRate: "konversiya",
      leadPipeline: "Lid bosqichlari",
      leadTemperature: "Lid harorati",
      botStatus: "Bot holati",
      planUsage: "Tarif va sarfiyot",
      noLeadsYet: "Hali lidlar yo'q",
      noBotsYet: "Hali botlar yo'q",
      createOne: "yarating",
      stNew: "Yangi",
      stContacted: "Bog'lanildi",
      stQualified: "Saralandi",
      stProposal: "Taklif",
      stWon: "Yutuq",
      stLost: "Yo'qotildi",
      tempHot: "Issiq",
      tempWarm: "Iliq",
      tempCold: "Sovuq",
      tempUnknown: "Noma'lum",
      botActive: "Faol",
      botDraft: "Qoralama",
      botPaused: "To'xtatilgan",
      botArchived: "Arxivlangan",
      total: "jami",
      leads: "lidlar",
      plan: "Tarif",
      conversationsMonth: "Oylik suhbatlar",
      unlimited: "Cheksiz",
      of: "dan",
      billingHint: "To'liq limitlar va tarif opsiyalari",
      billingLink: "To'lov sahifasi",
    },
    billing: {
      title: "To'lov",
      subtitle: "Obuna va tarif limitlarini boshqaring",
      loading: "To'lov ma'lumotlari yuklanmoqda…",
      loadError: "To'lov ma'lumotlarini yuklashda xatolik",
      checkoutSuccess: "Obunangiz faollashtirildi. Xush kelibsiz!",
      checkoutCanceled: "To'lov bekor qilindi. Tarifingizda o'zgarish yo'q.",
      stripeNotConfigured: "To'lov tizimi hali sozlanmagan. Qo'llab-quvvatlash bilan bog'laning.",
      checkoutFailed: "To'lov amalga oshmadi",
      noStripeLinked: "Stripe hisob bog'lanmagan. Avval pullik tarifga obuna bo'ling.",
      portalUnavailable: "Portal mavjud emas",
      currentPlan: "Joriy tarif",
      planLabel: "Tarif",
      perMonth: "/oy",
      activeSub: "Faol obunangiz",
      renews: "Yangilanadi",
      convPerMonth: "Suhbatlar/oy",
      bots: "Botlar",
      pdfFiles: "PDF fayllar",
      storage: "Xotira",
      unlimited: "Cheksiz",
      manageBilling: "To'lovni boshqarish",
      opening: "Ochilmoqda…",
      availablePlans: "Mavjud tariflar",
      mostPopular: "Eng mashhur",
      free: "Bepul",
      currentPlanBtn: "Joriy tarif",
      contactSupport: "Qo'llab-quvvatlash",
      upgrade: "Yangilash",
      redirecting: "Yo'naltirilmoqda…",
      manage: "Boshqarish",
      conversations: "suhbat",
      bot: "bot",
      storageUnit: "xotira",
      statusActive: "Faol",
      statusTrialing: "Sinov",
      statusPastDue: "Muddati o'tgan",
      statusCanceled: "Bekor qilingan",
      statusExpired: "Muddati tugagan",
      contactUs: "Bog'laning",
    },
    settings: {
      title: "Sozlamalar",
      subtitle: "Profil, xavfsizlik va akkaunt sozlamalarini boshqaring",
      loading: "Yuklanmoqda...",
      // Profil
      profile: "Profil",
      emailVerified: "Email tasdiqlangan",
      emailUnverified: "Email tasdiqlanmagan",
      active: "Faol",
      inactive: "Nofaol",
      userId: "Foydalanuvchi ID",
      memberSince: "A'zo bo'lgan sana",
      lastUpdated: "Oxirgi yangilanish",
      displayNamePlaceholder: "Ko'rsatiladigan ism",
      saving: "Saqlanmoqda...",
      save: "Saqlash",
      cancel: "Bekor qilish",
      editDisplayName: "Ismni tahrirlash",
      nameUpdated: "Ko'rsatiladigan ism yangilandi.",
      // Akkaunt xavfsizligi
      accountSecurity: "Akkaunt xavfsizligi",
      emailVerifiedMsg: "Email manzilingiz tasdiqlangan.",
      emailUnverifiedMsg: "Emailingiz hali tasdiqlanmagan. Barcha imkoniyatlarni yoqish uchun tasdiqlang.",
      sending: "Yuborilmoqda...",
      resendVerification: "Tasdiqlash emailini qayta yuborish",
      changePasswordHint: "Joriy parolni kiriting va yangi parolni tanlang (kamida 8 belgi).",
      changePassword: "Parolni o'zgartirish",
      passwordResetSent: "Parol tiklash havolasi yuborildi — pochta qutingizni tekshiring.",
      currentPassword: "Joriy parol",
      newPassword: "Yangi parol",
      confirmNewPassword: "Yangi parolni tasdiqlang",
      passwordsDoNotMatch: "Parollar mos kelmaydi",
      passwordTooShort: "Parol kamida 8 belgidan iborat bo'lishi kerak",
      passwordChanged: "Parol muvaffaqiyatli o'zgartirildi!",
      changingPassword: "O'zgartirilmoqda...",
      wrongCurrentPassword: "Joriy parol noto'g'ri",
      verificationSent: "Tasdiqlash emaili yuborildi — pochta qutingizni tekshiring.",
      // 2FA
      twoFactor: "Ikki bosqichli autentifikatsiya",
      twoFactorActivated: "Ikki bosqichli autentifikatsiya faollashtirildi!",
      twoFactorDisableConfirm: "Ikki bosqichli autentifikatsiyani o'chirishni xohlaysizmi?",
      twoFactorDisabled: "Ikki bosqichli autentifikatsiya o'chirildi.",
      twoFactorProtected: "Akkauntingiz TOTP bilan himoyalangan.",
      disable2fa: "2FA ni o'chirish",
      disabling: "O'chirilmoqda...",
      scanQrCode: "Ushbu QR kodni autentifikatsiya ilovangiz bilan skanerlang (Google Authenticator, Authy va h.k.), so'ng quyidagi kodni kiriting.",
      manualEntryKey: "Qo'lda kiritish kaliti:",
      recoveryCodes: "Qayta tiklash kodlari (xavfsiz saqlang):",
      totpPlaceholder: "6 raqamli kod",
      verifying: "Tekshirilmoqda...",
      activate: "Faollashtirish",
      twoFactorDesc: "Autentifikatsiya ilovasi orqali ikki bosqichli autentifikatsiyani yoqib, akkauntingizga qo'shimcha himoya qo'shing.",
      settingUp: "Sozlanmoqda...",
      setUp2fa: "2FA ni sozlash",
      // Sessiyalar
      activeSessions: "Faol sessiyalar",
      loadingSessions: "Sessiyalar yuklanmoqda...",
      noSessions: "Faol sessiyalar topilmadi.",
      started: "Boshlangan",
      lastUsed: "Oxirgi foydalanish",
      // Ish maydoni
      workspace: "Ish maydoni",
      billingPlans: "To'lovlar va tariflar",
      manageBots: "Botlarni boshqarish",
      // Ma'lumotlar va maxfiylik
      dataPrivacy: "Ma'lumotlar va maxfiylik",
      exportDesc: "Akkaunt ma'lumotlaringizning JSON nusxasini yuklab oling — profil, botlar, lidlar va obuna ma'lumotlari.",
      exporting: "Eksport qilinmoqda...",
      exportData: "Ma'lumotlarimni eksport qilish",
      exportSuccess: "Ma'lumotlar muvaffaqiyatli eksport qilindi.",
      // Xavfli zona
      dangerZone: "Xavfli zona",
      logoutAllDesc: "Barcha qurilmalardan chiqish barcha faol sessiyalarni, shu jumladan ushbu sessiyani ham bekor qiladi. Siz kirish sahifasiga yo'naltirilasiz.",
      signingOut: "Chiqilmoqda...",
      signOutAll: "Barcha qurilmalardan chiqish",
      logoutAllConfirm: "Barcha qurilmalardan chiqiladi. Davom etasizmi?",
      deleteAccountDesc: "Akkauntingiz va barcha bog'liq ma'lumotlar (botlar, suhbatlar, lidlar, fayllar) butunlay o'chiriladi.",
      cannotBeUndone: "qaytarib bo'lmaydi",
      absolutelySure: "Rostdan ham ishonchingiz komilmi?",
      deleting: "O'chirilmoqda...",
      yesDelete: "Ha, akkauntimni o'chirish",
      deleteAccount: "Akkauntimni o'chirish",
      // Telegram ulash
      telegramTitle: "Telegram bildirishnomalar",
      telegramDesc: "Botlaringiz yangi lead yig'ganda darhol xabar olish uchun Telegram akkauntingizni ulang.",
      telegramLink: "Telegramni ulash",
      telegramLinkedMsg: "Telegram akkauntingiz ulangan. Yangi lead bildirishnomalari Telegram chatga keladi.",
      telegramLinkedAt: "Ulangan",
      telegramConnected: "Ulangan",
      telegramUnlink: "Telegramni uzish",
      telegramUnlinking: "Uzilmoqda...",
      telegramNotConfigured: "Telegram bildirishnomalar hali ushbu platforma uchun sozlanmagan. Tafsilotlar uchun qo'llab-quvvatlash xizmatiga murojaat qiling.",
    },
    notifications: {
      title: "Bildirishnomalar",
      bell: "Bildirishnomalar",
      empty: "Hali bildirishnomalar yo'q",
      markAllRead: "Barchasini o'qilgan deb belgilash",
    },
    wizard: {
      title: "Bot yaratish",
      lead: "Bir necha tezkor qadam — bir ekranda bitta. Jarayoningiz ushbu qurilmada avtomatik saqlanadi (Telegram tokenlari brauzerda saqlanmaydi).",
      assistiveHint: "Davom etish uchun Davom tugmasini, oldingi tanlovlarni ko'rish uchun Orqaga tugmasini bosing.",
      loading: "Saqlangan jarayoningiz yuklanmoqda...",
      step: "Qadam",
      of: "/",
      back: "Orqaga",
      continue: "Davom etish",
      exitToBots: "Botlarga qaytish",
      skipForNow: "Hozircha o'tkazib yuborish",
      createBot: "Bot yaratish",
      creatingBot: "Bot yaratilmoqda...",
      stepNiche: "Soha",
      stepGoal: "Maqsad",
      stepBasics: "Asosiy",
      stepChannel: "Kanal",
      stepKnowledge: "Bilim",
      stepReview: "Ko'rib chiqish",
      nicheTitle: "Bu bot nima uchun?",
      nicheDesc: "Biznesingizga mos kontekstni tanlang. Keyinroq aniqlashtirish mumkin.",
      goalTitle: "Bot nima qilishi kerak?",
      goalDesc: "Asosiy natijani tanlang — ohang va jarayonlar shunga moslashadi.",
      basicsTitle: "Nom va ovoz",
      basicsDesc: "Botga aniq nom bering va tashrif buyuruvchilarga qanday eshitilishini belgilang.",
      channelTitle: "Odamlar siz bilan qayerda gaplashadi",
      channelDesc: "Sayt vidjeti Telegram tokenisiz ishlaydi. Telegram (yoki ikkalasi) uchun BotFather tokeni kerak.",
      knowledgeTitle: "Javoblarni kontentingizga asoslang",
      knowledgeDesc: "PDF fayllarni yuklang va botga ishonchli biznes kontekst berish uchun eslatmalar qo'shing.",
      reviewTitle: "Ko'rib chiqish va yaratish",
      reviewDesc: "Tanlovlaringizni tasdiqlang. Holat backend qoidalariga mos keladi.",
      nicheLoading: "Qo'llab-quvvatlanadigan sohalar yuklanmoqda...",
      nicheLegend: "Soha",
      nicheFallback: "Soha ro'yxatini serverdan yangilab bo'lmadi. Saqlangan standartlar ko'rsatilmoqda — ulanishingizni tekshiring.",
      goalLegend: "Maqsad",
      goalSupport: "Qo'llab-quvvatlash",
      goalSupportHint: "Muammolarni tezkor hal qilish va yo'naltirish.",
      goalSales: "Sotuv",
      goalSalesHint: "Tashrif buyuruvchilarni kvalifikatsiya va keyingi qadamlar bilan lidlarga aylantirish.",
      goalFaq: "Ko'p so'raladigan savollar",
      goalFaqHint: "Tez-tez beriladigan savollarga qisqa va ishonchli javoblar berish.",
      goalConsulting: "Konsalting",
      goalConsultingHint: "Kontekst yig'ish va ekspert uslubidagi tavsiyalar berish.",
      botName: "Bot nomi",
      botNameHelp: "Ish maydoningiz va kanal sozlamalarida ko'rsatiladi.",
      botNamePlaceholder: "masalan: Do'kon Yordamchisi",
      toneLegend: "Ohang",
      toneHelp: "Ohang ixtiyoriy. Bo'sh qoldirib, keyinroq sozlashingiz mumkin.",
      toneFriendly: "Do'stona va qisqa",
      toneProfessional: "Professional va rasmiy",
      tonePlayful: "Quvnoq va yengil",
      toneNeutral: "Neytral va aniq",
      languageLabel: "Til",
      languageHelp: "Bu qoralama sifatida saqlanadi va backend tayyor bo'lganda ko'p tilli xatti-harakatga moslashadi.",
      shortDesc: "Qisqa tavsif",
      shortDescPlaceholder: "masalan: Yangi mijozlarga tariflarni tanlashda yordam beradi.",
      openingLine: "Ochilish matni",
      openingLineHelp: "Soha va til uchun tavsiya etilgan standartni ishlatish uchun bo'sh qoldiring.",
      defaultWelcome: "Salom! Buyurtmalar yoki mahsulot savollari bo'yicha yordam bera olaman.",
      optional: "(ixtiyoriy)",
      channelHint: "Sayt vidjeti Telegram tokenini talab qilmaydi. Agar Telegram yoki Ikkala variantni tanlasangiz, backend faqat BotFather tokeni va vebhuk muvaffaqiyatli ro'yxatdan o'tgandan keyin botni faol deb belgilaydi.",
      channelLegend: "Kanal",
      chWebsite: "Sayt vidjeti",
      chWebsiteHint: "Telegram tokeni kerak emas — bot veb-kanal uchun faol bo'lishi mumkin.",
      chTelegram: "Telegram",
      chTelegramHint: "Bot faol bo'lishi uchun BotFather tokeni kerak.",
      chBoth: "Ikkala",
      chBothHint: "Veb faol bo'lishi mumkin; Telegram uchun token va vebhuk kerak.",
      proPlus: "Pro+",
      upgradeForTelegram: "Telegramdan foydalanish uchun Pro yoki undan yuqori tarifga o'ting.",
      telegramRequiresPro: "Telegram uchun Pro tarif yoki undan yuqori kerak.",
      upgradeNow: "Yangilash",
      telegramToken: "Telegram bot tokeni",
      telegramTokenHelp: "BotFather dan. Bu qadamni o'tkazib yuborsangiz, bot kanal kutilmoqda holatida yaratiladi — Telegram bot sozlamalaridan ulanguningizcha faol bo'lmaydi.",
      telegramTokenPlaceholder: "Telegramda ishga tushirish uchun tokenni joylashtiring",
      channelPending: "kanal kutilmoqda",
      knowledgeHint: "Bilim bazasi botga ishonchli biznes kontekstini beradi. PDF fayllarni shu yerda yuklang — bot yaratilgandan keyin serverga avtomatik yuboriladi.",
      typicalSources: "Odatiy manbalar",
      srcPdf: "PDF hujjatlar",
      srcFaq: "Ko'p so'raladigan savollar",
      srcService: "Xizmat ma'lumotlari",
      srcPricing: "Narxlar haqida",
      pdfLiveTitle: "PDF lar bot sahifasida",
      pdfLiveBody: "Bot yaratilgandan keyin uni Botlar sahifasidan oching va Bilim bazasidan foydalaning.",
      notesLabel: "Eslatmalar",
      notesHelp: "Xohlasangiz URL yoki muhim faktlarni hozir qo'shing. Bo'sh qoldirish yaratishga to'sqinlik qilmaydi.",
      notesPlaceholder: "masalan: Narxlar sahifasi URL, qaytarish siyosati...",
      uploadDropTitle: "PDF fayllarni shu yerga tashlang yoki tanlash uchun bosing",
      uploadDropMeta: "Faqat PDF · Har bir fayl max 20 MB",
      removeFile: "O'chirish",
      fileTooLarge: "Fayl juda katta (max 20 MB)",
      fileNotPdf: "Faqat PDF fayllar qabul qilinadi",
      pendingUploadNote: "Fayllar bot yaratilgandan keyin avtomatik yuklanadi",
      revFiles: "PDF fayllar",
      noFilesAttached: "Fayl biriktirilmagan",
      filesReady: "ta fayl yuklashga tayyor",
      uploadingFiles: "Bilim fayllari yuklanmoqda...",
      uploadComplete: "Barcha fayllar muvaffaqiyatli yuklandi!",
      uploadPartialFail: "Ba'zi fayllar yuklanmadi",
      revNiche: "Soha",
      revGoal: "Maqsad",
      revName: "Nom",
      revLanguage: "Til",
      revTone: "Ohang",
      revChannel: "Kanal",
      revTelegramToken: "Telegram tokeni",
      revKnowledge: "Bilim eslatmalari",
      tokenNA: "Tegishli emas",
      tokenProvided: "Kiritilgan (serverda tekshiriladi)",
      tokenNotProvided: "Kiritilmagan — kanal kutilmoqda holati kutilmoqda",
      knowledgeSkipped: "O'tkazib yuborilgan",
      knowledgeNone: "Yo'q (yaratilgandan keyin fayllarni yuklang)",
      expectedStatus: "Kutilayotgan ish maydoni holati",
      outcomeActiveWeb: "Faol (veb)",
      outcomeActiveWebDetail: "Telegram tokeni kerak emas. Bot sayt vidjeti orqali ishlatilishi mumkin.",
      outcomeActiveTg: "Faol (agar Telegram tokenni qabul qilsa)",
      outcomeActiveTgDetail: "Biz tokenni tekshiramiz va serverda vebhukni ro'yxatdan o'tkazamiz.",
      outcomePending: "Kanal kutilmoqda",
      outcomePendingDetail: "Telegram tokenisiz saqlangan. Bot sozlamalaridan Telegram panelidan sozlashni yakunlang.",
      outcomeDraft: "Qoralama",
      outcomeDraftDetail: "Natijani ko'rish uchun kanal tanlang.",
      doneActiveTitle: "Bot saqlandi va faol",
      doneActiveBody: "Ish maydoni holati serverga mos keladi: bu bot tayyor kanallar uchun faol.",
      donePendingTitle: "Bot saqlandi — sozlash tugallanmagan",
      donePendingBody: "Telegram token va vebhuk bilan ulanmaguncha holat kanal kutilmoqda.",
      doneDefaultTitle: "Bot saqlandi",
      doneDefaultBody: "Botlar ish maydoningizga o'tilmoqda...",
      serverStatus: "Server holati:",
      primaryChannel: "asosiy kanal:",
      openBots: "Botlarni ochish",
    },
  },
  superadmin: {
    nav: {
      overview:     "Platforma Ko'rinishi",
      users:        "Foydalanuvchilar",
      bots:         "Botlar",
      billing:      "To'lovlar",
      aiUsage:      "AI Sarfi",
      auditLog:     "Audit Jurnali",
      featureFlags: "Flaglar",
      support:      "Yordam",
      coupons:      "Kuponlar",
      analytics:    "Segment Tahlili",
      abuse:        "Suiiste'mol",
      export:       "Export",
      campaigns:    "Email Yuborish",
      webhookLogs:  "Webhook Jurnali",
    },
    common: {
      loading: "Yuklanmoqda...",
      error: "Xatolik",
      save: "Saqlash",
      saving: "Saqlanmoqda...",
      cancel: "Bekor",
      create: "Yaratish",
      edit: "Tahrir",
      delete: "O'chirish",
      deleting: "O'chirilmoqda...",
      confirm: "Tasdiqlash",
      total: "Jami",
      noRecords: "Yozuv topilmadi",
      actions: "Amallar",
      status: "Holat",
      period: "Davr",
      allStatuses: "Barcha statuslar",
      allPlans: "Barcha planlar",
      allTypes: "Barcha turlar",
      allActions: "Barcha amallar",
      clear: "Tozalash",
      view: "Ko'rish",
      back: "Orqaga",
    },
    flags: {
      total: "ta flag",
      newFlag: "+ Yangi flag",
      key: "Kalit (key)",
      state: "Holat",
      plan: "Plan",
      description: "Tavsif",
      updated: "Yangilangan",
      enabled: "Yoqilgan",
      disabled: "O'chirilgan",
      toggleTitle: "Holatni o'zgartirish",
      createTitle: "Yangi flag yaratish",
      editTitle: "Flagni tahrirlash",
      keyLabel: "Kalit (key) *",
      keyHelp: "Faqat kichik harf, raqam va _ belgisi",
      keyPlaceholder: "misol: advanced_analytics",
      descLabel: "Tavsif (ixtiyoriy)",
      descPlaceholder: "Bu flag nima uchun...",
      targetPlan: "Maqsad plan (ixtiyoriy)",
      globalAllPlans: "Global (barcha planlar)",
      enableOnCreate: "Hozir yoqilgan holda yaratish",
      deleteTitle: "Flagni o'chirish",
      deleteConfirm: "flagini o'chirishni tasdiqlaysizmi?",
      deleteWarn: "Bu amalni qaytarib bo'lmaydi.",
      yesDelete: "Ha, o'chir",
      emptyState: "Hech qanday flag yo'q. Yangi flag yarating.",
      targetUsers: "Maqsadli foydalanuvchilar",
      targetUsersHelp: "Aniq foydalanuvchilar uchun yoqish emaillarini kiriting",
      addEmail: "Qo'shish",
      emailPlaceholder: "user@example.com",
      usersTargeted: "ta foydalanuvchi",
      noUserTarget: "Foydalanuvchi maqsadlanmagan",
      invalidEmail: "Email format noto'g'ri",
    },
    billing: {
      user: "Foydalanuvchi",
      plan: "Plan",
      periodStart: "Davr boshi",
      periodEnd: "Davr oxiri",
      canceled: "Bekor qilingan",
      stripe: "Stripe",
      changePlan: "Plan o'zgartirish",
      changePlanTitle: "Plan o'zgartirish",
      newPlan: "Yangi plan",
      reason: "Sabab (ixtiyoriy)",
      reasonPlaceholder: "Admin eslatmasi...",
      blocked: "Bloklangan",
      manual: "Manual",
      free: "bepul",
      statusActive: "Aktiv",
      statusTrialing: "Sinov",
      statusPastDue: "To'lov kechikdi",
      statusCanceled: "Bekor qilindi",
      statusExpired: "Muddati tugadi",
      totalActive: "Jami faol",
      totalPastDue: "Muddati o'tgan",
      estimatedMrr: "Taxminiy MRR",
      mrrNote: "Joriy sahifadagi plan narxlari asosida",
    },
    aiUsage: {
      periodLabel: "Davr:",
      summaryTitle: "platformaning umumiy AI sarfi",
      totalCalls: "Jami so'rovlar",
      successful: "Muvaffaqiyatli",
      failed: "Xato",
      successRate: "Muvaffaqiyat darajasi",
      totalTokens: "Jami tokenlar",
      totalCost: "Jami xarajat",
      dailyHistory: "Kunlik tarix",
      date: "Sana",
      calls: "So'rovlar",
      tokens: "Tokenlar",
      costUsd: "Xarajat (USD)",
      topConsumers: "Eng ko'p tokenlar sarflaganlar (Top 10)",
      user: "Foydalanuvchi",
      cost: "Xarajat",
      noData: "Bu davr uchun AI sarfi ma'lumotlari mavjud emas.",
    },
    auditLog: {
      time: "Vaqt",
      action: "Amal",
      entityType: "Tur / Entity ID",
      actor: "Aktor",
      meta: "Meta",
      snapshot: "Snapshot",
      snapshotTitle: "Snapshot",
      before: "Oldin (before)",
      after: "Keyin (after)",
      metadata: "Metadata",
      sinceDate: "Dan boshlab (sana)",
    },
    export: {
      intro: "Platforma ma'lumotlarini CSV formatda eksport qiling — hisobot, audit va moliyaviy tahlil uchun.",
      download: "Yuklab olish",
      downloading: "Yuklanmoqda...",
      downloadFailed: "Yuklab olib bo'lmadi",
      usersLabel: "Foydalanuvchilar",
      usersDesc: "Barcha ro'yxatdan o'tganlar — ID, email, rol, holat, sanalar.",
      subscriptionsLabel: "Obunalar",
      subscriptionsDesc: "Barcha obunalar — plan, holat, Stripe ID, billing davrlari.",
      aiUsageLabel: "AI Sarfi",
      aiUsageDesc: "Botlar bo'yicha kunlik AI sarfi — so'rovlar, tokenlar, xarajat.",
      couponsLabel: "Kuponlar",
      couponsDesc: "Barcha kupon kodlari — chegirma, foydalanish, muddati.",
      quickPresets: "Tezkor sozlamalar",
      preset7d: "Oxirgi 7 kun",
      preset30d: "Oxirgi 30 kun",
      preset90d: "Oxirgi 90 kun",
      presetYtd: "Yil boshidan",
    },
    overview: {
      intro: "Platformaning jonli statistikasi. Foydalanuvchilar, botlar va billingni ko'rish uchun yon paneldan foydalaning.",
      loadingOverview: "Yuklanmoqda...",
      usersAndBots: "Foydalanuvchilar va Botlar",
      registeredUsers: "Ro'yxatdan o'tganlar",
      activeUsers: "Faol foydalanuvchilar",
      totalBots: "Jami botlar",
      activeBots: "Faol botlar",
      leads: "Lidlar",
      conversations: "Suhbatlar",
      billingRevenue: "Billing va Daromad",
      mrr: "MRR",
      mrrSub: "Oylik takrorlanuvchi daromad",
      paidActive: "Pulli faol",
      paidActiveSub: "Faol pulli obunachilar",
      freePlan: "Bepul plan",
      freePlanSub: "Bepul tarifda",
      pastDue: "Muddati o'tgan",
      pastDueSub: "To'lov amalga oshmagan",
      canceled: "Bekor qilingan",
      canceledSub: "Ketganlar",
      planDistribution: "Plan taqsimoti",
      generatedAt: "Yaratilgan vaqt",
      viewBilling: "Billing tafsilotlarini ko'rish",
      planChart: "Plan taqsimoti",
      autoRefresh: "Avto-yangilash",
      refreshEvery: "Har",
      seconds: "s",
      recentActivity: "So'nggi faoliyat",
    },
    users: {
      intro: "Barcha hisob yozuvlari. Batafsil va moderatsiya uchun qatorni oching.",
      showingRange: "Ko'rsatilmoqda",
      noUsers: "Foydalanuvchilar yo'q",
      selected: "tanlangan",
      suspend: "To'xtatish",
      activate: "Faollashtirish",
      applyTo: "Qo'llash",
      previous: "Oldingi",
      next: "Keyingi",
      selectAll: "Hammasini tanlash",
      email: "Email",
      role: "Rol",
      status: "Holat",
      bots: "Botlar",
      updated: "Yangilangan",
      inactive: "Nofaol",
      suspended: "To'xtatilgan",
      active: "Faol",
      confirmBulkTitle: "Ommaviy amalni tasdiqlash",
      confirmBulkHint: "Tanlangan foydalanuvchilarga qo'llash?",
      reasonOptional: "Sabab (ixtiyoriy)",
      reasonPlaceholder: "To'xtatish sababi...",
      processing: "Bajarilmoqda...",
      confirmAction: "Tasdiqlash",
      bulkSuccess: "Ommaviy amal bajarildi",
    },
    botsList: {
      intro: "Barcha botlar. Konfiguratsiya va moderatsiya uchun qatorni oching.",
      showingRange: "Ko'rsatilmoqda",
      noBots: "Botlar yo'q",
      previous: "Oldingi",
      next: "Keyingi",
      bot: "Bot",
      owner: "Egasi",
      status: "Holat",
      channels: "Kanallar",
      updated: "Yangilangan",
      platformSuspended: "Platforma to'xtatgan",
      widget: "Widget",
      telegram: "Telegram",
      selected: "tanlangan",
      bulkSuspend: "Tanlanganlarni to'xtatish",
      bulkActivate: "Tanlanganlarni faollashtirish",
      bulkSuspendTitle: "Botlarni ommaviy to'xtatish",
      bulkActivateTitle: "Botlarni ommaviy faollashtirish",
      bulkApplyTo: "Bu amal quyidagilarga tatbiq etiladi:",
      botsCount: "ta bot",
      bulkReason: "Sabab (ixtiyoriy)",
      bulkReasonPlaceholder: "Masalan: Qoida buzilishi, spam kontent...",
    },
    userDetail: {
      loadingUser: "Yuklanmoqda...",
      backToUsers: "Foydalanuvchilarga qaytish",
      inspectTenant: "Tenant tekshiruvi (faqat o'qish, audit qilinadi)",
      email: "Email",
      name: "Ism",
      role: "Rol",
      active: "Faol",
      verified: "Tasdiqlangan",
      password: "Parol",
      suspendedAt: "To'xtatilgan sana",
      suspensionNote: "To'xtatish izohi",
      oauthProviders: "OAuth provayderlar",
      bots: "Botlar",
      created: "Yaratilgan",
      updated: "Yangilangan",
      yes: "Ha",
      no: "Yo'q",
      set: "O'rnatilgan",
      notSet: "O'rnatilmagan",
      activateUser: "Foydalanuvchini faollashtirish",
      cannotSuspendSelf: "O'z hisobingizni bu konsoldan to'xtata olmaysiz.",
      suspendUser: "Foydalanuvchini to'xtatish",
      impersonation: "Impersonatsiya",
      impersonationDesc: "Ushbu foydalanuvchi hisobini ko'rish uchun 15 daqiqalik token yarating. Audit jurnaliga yoziladi.",
      generating: "Yaratilmoqda...",
      generateToken: "Impersonatsiya tokeni yaratish",
      tokenHint: "Token (15 daq) — nusxalab Bearer token sifatida foydalaning:",
      copy: "Nusxalash",
      dismiss: "Yopish",
      planOverride: "Plan o'zgartirish",
      plan: "Plan",
      reasonOptional: "Sabab (ixtiyoriy)",
      reasonPlaceholder: "Ichki sabab...",
      applying: "Qo'llanmoqda...",
      applyOverride: "O'zgartirish",
      userSuspended: "Foydalanuvchi to'xtatildi.",
      userActivated: "Foydalanuvchi faollashtirildi.",
      planOverridden: "Plan o'zgartirildi.",
      suspendTitle: "Foydalanuvchini to'xtatish",
      suspendDesc: "Hisob nofaol holatga o'tadi va kirishni bloklaydi. Ixtiyoriy ichki izoh saqlanadi.",
      suspendConfirm: "To'xtatish",
    },
    botDetail: {
      loadingBot: "Yuklanmoqda...",
      backToBots: "Botlarga qaytish",
      name: "Nomi",
      botId: "Bot ID",
      ownerEmail: "Egasi email",
      ownerId: "Egasi ID",
      niche: "Nisha",
      goal: "Maqsad",
      status: "Holat",
      providerModel: "Provider / model",
      widget: "Widget",
      telegram: "Telegram",
      platformSuspended: "Platforma to'xtatgan",
      suspensionNote: "To'xtatish izohi",
      welcome: "Xush kelibsiz xabar",
      tone: "Ohang",
      language: "Til",
      description: "Tavsif",
      temperature: "Temperatura",
      maxOutputTokens: "Maks tokenlar",
      created: "Yaratilgan",
      updated: "Yangilangan",
      configured: "Sozlangan",
      notConfigured: "Sozlanmagan",
      connected: "Ulangan",
      notConnected: "Ulanmagan",
      clearSuspension: "To'xtatishni bekor qilish",
      platformSuspendBot: "Botni platforma to'xtatishi",
      botSuspended: "Bot platforma tomonidan to'xtatildi.",
      suspensionCleared: "Platforma to'xtatishi bekor qilindi.",
      suspendBotTitle: "Botni to'xtatish",
      suspendBotDesc: "Widget, Telegram AI javoblari va test chat bloklanadi. Egasi workspace o'zgarmaydi.",
      suspendBotConfirm: "Botni to'xtatish",
      performance: "Ishlash ko'rsatkichlari",
      conversations: "Suhbatlar",
      leadsGenerated: "Yaratilgan lidlar",
      aiCalls: "AI so'rovlar",
      aiTokens: "AI tokenlar",
    },
    support: {
      loadError: "Tiketlarni yuklashda xatolik.",
      updateError: "Tiketni yangilashda xatolik.",
      allStatuses: "Barcha holatlar",
      statusOpen: "Ochiq",
      statusInProgress: "Jarayonda",
      statusResolved: "Hal qilingan",
      statusClosed: "Yopilgan",
      allPriorities: "Barcha ustuvorliklar",
      priorityLow: "Past",
      priorityNormal: "O'rta",
      priorityHigh: "Yuqori",
      ticketsCount: "tiketlar",
      subject: "Mavzu",
      user: "Foydalanuvchi",
      status: "Holat",
      priority: "Ustuvorlik",
      created: "Yaratilgan",
      actions: "Amallar",
      noTickets: "Tiketlar topilmadi.",
      notePrefix: "Izoh:",
      edit: "Tahrir",
      prevPage: "Oldingi",
      nextPage: "Keyingi",
      pageOf: "Sahifa",
      updateTitle: "Tiketni yangilash",
      statusLabel: "Holat",
      priorityLabel: "Ustuvorlik",
      adminNote: "Admin izohi",
      notePlaceholder: "Tiket uchun izoh yozing...",
      replyTitle: "Tiket tafsilotlari",
      ticketBody: "Xabar",
      replyLabel: "Admin javobi",
      replyPlaceholder: "Javobingizni yozing...",
      replyAndProgress: "Javob va jarayonga o'tkazish",
      replyAndResolve: "Javob va hal qilish",
      submittedAt: "Yuborilgan",
      resolvedAt: "Hal qilingan",
      noReplyYet: "Hali javob yo'q",
      previousReply: "Oldingi javob",
      cancel: "Bekor",
      saving: "Saqlanmoqda...",
      save: "Saqlash",
    },
    abuse: {
      loadError: "Suiste'mol hisobotini yuklashda xatolik.",
      suspendError: "To'xtatish amalga oshmadi.",
      periodLabel: "Davr (kunlar):",
      day1: "1 kun",
      day3: "3 kun",
      day7: "7 kun",
      minCalls: "Min chaqiruvlar:",
      refresh: "Yangilash",
      highUsageTitle: "Yuqori sarfli hisoblar",
      user: "Foydalanuvchi",
      calls: "Chaqiruvlar",
      failed: "Xato",
      tokens: "Tokenlar",
      cost: "Xarajat",
      errorRate: "Xato darajasi",
      actions: "Amallar",
      noHighUsage: "Yuqori sarfli hisoblar aniqlanmadi.",
      suspend: "To'xtatish",
      topErrorsTitle: "Top xato kodlari",
      errorCode: "Xato kodi",
      occurrences: "Takrorlanish",
      noErrors: "Xato ma'lumotlari yo'q.",
      suspendedUser: "To'xtatildi",
      failedToSuspend: "To'xtata olmadi",
    },
    campaigns: {
      segmentAllUsers: "Barcha faol foydalanuvchilar",
      segmentPastDue: "Muddati o'tganlar",
      segmentFreePlan: "Bepul plan",
      segmentPaidUsers: "Pulli foydalanuvchilar",
      segmentInactive7d: "7+ kun nofaol",
      loadError: "Kampaniyalarni yuklashda xatolik.",
      createError: "Kampaniya yaratishda xatolik.",
      updateError: "Kampaniyani yangilashda xatolik.",
      sendError: "Kampaniya yuborishda xatolik.",
      deleteError: "Kampaniyani o'chirishda xatolik.",
      newCampaign: "+ Yangi kampaniya",
      campaignsCount: "kampaniyalar",
      subject: "Mavzu",
      segment: "Segment",
      status: "Holat",
      sentFailed: "Yuborilgan / Xato",
      sentAt: "Yuborilgan sana",
      actions: "Amallar",
      noCampaigns: "Kampaniyalar hali yo'q.",
      recipients: "qabul qiluvchi",
      failedCount: "xato",
      preview: "Ko'rish",
      edit: "Tahrir",
      send: "Yuborish",
      delete: "O'chirish",
      prevPage: "Oldingi",
      nextPage: "Keyingi",
      pageOf: "Sahifa",
      newTitle: "Yangi email kampaniya",
      subjectLabel: "Mavzu",
      targetSegment: "Maqsadli segment",
      bodyLabel: "Matn (HTML)",
      cancel: "Bekor",
      creating: "Yaratilmoqda...",
      createDraft: "Qoralama yaratish",
      editTitle: "Kampaniyani tahrirlash",
      bodyHtml: "Matn HTML",
      saving: "Saqlanmoqda...",
      saveChanges: "Saqlash",
      previewTitle: "Ko'rish",
      segmentLabel: "Segment",
      close: "Yopish",
      sendTitle: "Kampaniyani yuborish?",
      sendConfirm: "Kampaniya darhol yuboriladi. Bu amalni bekor qilib bo'lmaydi.",
      sending: "Yuborilmoqda...",
      confirmSend: "Yuborishni tasdiqlash",
      deleteTitle: "Kampaniyani o'chirish?",
      deleteConfirm: "Ishonchingiz komilmi? Bu amalni bekor qilib bo'lmaydi.",
      deleting: "O'chirilmoqda...",
      campaignCreated: "Kampaniya yaratildi",
      campaignUpdated: "Kampaniya yangilandi.",
      campaignSending: "Kampaniya yuborilmoqda",
      templateLabel: "Shablon",
      tplBlank: "Bo'sh",
      tplBlankDesc: "Noldan boshlash",
      tplWelcome: "Xush kelibsiz",
      tplWelcomeDesc: "Yangi foydalanuvchilar uchun onboarding",
      tplAnnouncement: "E'lon",
      tplAnnouncementDesc: "Mahsulot yangiligi yoki yangilik",
      tplPromotion: "Aksiya",
      tplPromotionDesc: "Chegirma yoki maxsus taklif",
      tplReengagement: "Qayta jalb",
      tplReengagementDesc: "Nofaol foydalanuvchilarni qaytarish",
    },
    coupons: {
      loadError: "Kuponlarni yuklashda xatolik.",
      createError: "Kupon yaratishda xatolik.",
      updateError: "Kuponni yangilashda xatolik.",
      deleteError: "Kuponni o'chirishda xatolik.",
      codeExists: "Kupon kodi allaqachon mavjud.",
      newCoupon: "+ Yangi kupon",
      couponsCount: "kuponlar",
      code: "Kod",
      discount: "Chegirma",
      plan: "Plan",
      uses: "Foydalanish",
      expires: "Muddati",
      status: "Holat",
      actions: "Amallar",
      noCoupons: "Kuponlar hali yo'q.",
      allPlans: "barchasi",
      active: "faol",
      inactive: "nofaol",
      edit: "Tahrir",
      delete: "O'chirish",
      createTitle: "Kupon yaratish",
      codeLabel: "Kod (katta harf, masalan LAUNCH50)",
      typeLabel: "Turi",
      valueLabel: "Qiymati",
      percentType: "Foiz (%)",
      usdType: "USD ($)",
      targetPlan: "Maqsadli plan (ixtiyoriy)",
      maxUses: "Maks foydalanish (ixtiyoriy)",
      expiresAt: "Tugash sanasi (ixtiyoriy)",
      cancel: "Bekor",
      creating: "Yaratilmoqda...",
      create: "Yaratish",
      editTitle: "Tahrir",
      activeLabel: "Faol",
      inactiveLabel: "Nofaol",
      clearExpiry: "Muddatni olib tashlash (cheklanmagan)",
      saving: "Saqlanmoqda...",
      save: "Saqlash",
      deleteTitle: "Kuponni o'chirish?",
      deleteConfirm: "Haqiqatan ham bu kuponni o'chirmoqchimisiz? Bu amalni bekor qilib bo'lmaydi.",
      deleting: "O'chirilmoqda...",
      couponCreated: "Kupon yaratildi.",
      analyticsActive: "Faol kuponlar",
      analyticsRedemptions: "Jami ishlatishlar",
      analyticsExpired: "Muddati tugagan",
      analyticsMaxedOut: "Limiti tugagan",
      analyticsAvgDiscount: "O'rtacha chegirma",
    },
    webhooks: {
      loadError: "Webhook jurnallarini yuklashda xatolik.",
      failedTotal: "jami muvaffaqiyatsiz webhooklar",
      showFailedOnly: "Faqat xatolarni ko'rsatish",
      allSources: "Barcha manbalar",
      stripe: "Stripe",
      telegram: "Telegram",
      allStatuses: "Barcha holatlar",
      received: "Qabul qilingan",
      processed: "Bajarilgan",
      failed: "Xato",
      clearDates: "Sanalarni tozalash",
      logsCount: "jurnallar",
      source: "Manba",
      eventType: "Hodisa turi",
      status: "Holat",
      bot: "Bot",
      receivedAt: "Qabul qilingan",
      details: "Tafsilotlar",
      noLogs: "Webhook jurnallari topilmadi.",
      view: "Ko'rish",
      prevPage: "Oldingi",
      nextPage: "Keyingi",
      pageOf: "Sahifa",
      close: "Yopish",
    },
    tenant: {
      loadingInspection: "Tekshiruv yuklanmoqda...",
      backToUser: "Foydalanuvchiga qaytish",
      intro: "Faqat o'qish uchun operatsion snapshot. Bu sahifani ochish audit hodisasini yaratadi.",
      leads: "Lidlar",
      conversations: "Suhbatlar",
      aiCalls: "AI chaqiruvlar",
      aiFailures: "AI xatolar",
      tokensWindow: "Tokenlar",
      tenantSummary: "Tenant xulosasi",
      email: "Email",
      role: "Rol",
      active: "Faol",
      botsProfile: "Botlar (profil)",
      yes: "Ha",
      no: "Yo'q",
      channelMix: "Kanal taqsimoti (suhbatlar)",
      noConversations: "Suhbatlar hali yo'q.",
      channel: "Kanal",
      botsShown: "Botlar",
      noBotsForTenant: "Bu tenant uchun botlar yo'q.",
      bot: "Bot",
      status: "Holat",
      channels: "Kanallar",
      widget: "Widget",
      telegram: "Telegram",
      aiUsageWindow: "AI sarfi oynasi",
      dailyRollup: "Kunlik AI sarfi (so'nggi kunlar)",
      noDailyData: "Diapazon uchun kunlik ma'lumotlar yo'q.",
      date: "Sana",
      requests: "So'rovlar",
      tokens: "Tokenlar",
      costUsd: "Narx (USD)",
      recentErrors: "So'nggi AI xatolari",
      noFailedCalls: "Bu tenant uchun muvaffaqiyatsiz AI chaqiruvlar yo'q.",
      when: "Qachon",
      model: "Model",
      code: "Kod",
    },
    analytics: {
      channelWebWidget: "Web Widget",
      channelTelegram: "Telegram",
      channelAdminTest: "Admin Test",
      loadError: "Analitikani yuklashda xatolik.",
      periodLabel: "Davr: oxirgi",
      channelDistribution: "Kanal taqsimoti",
      noConversationData: "Suhbat ma'lumotlari hali yo'q.",
      userSignups: "Ro'yxatdan o'tishlar",
      noSignupData: "Bu davr uchun ro'yxatdan o'tish ma'lumotlari yo'q.",
      date: "Sana",
      newUsers: "Yangi foydalanuvchilar",
      bar: "Grafik",
      planSegments: "Plan segmentlari",
      plan: "Plan",
      status: "Holat",
      count: "Soni",
      churnByPlan: "Ketish (plan bo'yicha)",
      canceled: "Bekor qilingan",
      noChurnData: "Ketish ma'lumotlari yo'q.",
      botsByNiche: "Nisha bo'yicha botlar",
      niche: "Nisha",
      bots: "Botlar",
      noData: "Ma'lumot yo'q.",
      botsByGoal: "Maqsad turi bo'yicha botlar",
      signupChart: "Ro'yxatdan o'tish trendi",
      channelChart: "Kanal taqsimoti",
      goal: "Maqsad",
    },
    moderation: {
      internalNote: "Ichki izoh (ixtiyoriy)",
      internalNotePlaceholder: "Ichki izoh (ixtiyoriy, maks 1024 belgi)",
      cancel: "Bekor",
    },
  },
  common: {
    loading: "Yuklanmoqda...",
    error: "Xatolik yuz berdi",
    save: "Saqlash",
    cancel: "Bekor qilish",
    delete: "O'chirish",
    edit: "Tahrirlash",
    back: "Orqaga",
    next: "Keyingi",
    finish: "Tugatish",
    optional: "ixtiyoriy",
    or: "yoki",
  },
};

const ru: Translations = {
  nav: {
    features: "Возможности",
    pricing: "Цены",
    faq: "FAQ",
    login: "Войти",
    getStarted: "Начать",
    dashboard: "Панель управления",
    logout: "Выйти",
    language: "Язык",
  },
  hero: {
    badge: "Платформа AI-генерации лидов",
    headline: "Превращайте посетителей в",
    headlineAccent: "Реальных Клиентов",
    subtext:
      "Создайте умного AI-бота, который общается с посетителями, выявляет их потребности и передаёт их как лиды — на вашем сайте или в Telegram. Без кода.",
    cta: "Создать Бота — Бесплатно",
    ctaSecondary: "Как это работает",
    trustedBy: "Доверяют компании по всему миру",
  },
  stats: {
    bots: "500+",
    botsLabel: "Активных Ботов",
    leads: "10K+",
    leadsLabel: "Сгенерировано Лидов",
    uptime: "99.9%",
    uptimeLabel: "Время работы",
  },
  howItWorks: {
    title: "Как Это Работает",
    subtitle: "От регистрации до первого квалифицированного лида за минуты.",
    steps: [
      { title: "Регистрация", desc: "Создайте бесплатный аккаунт за несколько секунд." },
      {
        title: "Выберите нишу",
        desc: "Расскажите боту, что вы продаёте и кому помогаете.",
      },
      {
        title: "Загрузите знания",
        desc: "Добавьте PDF или заметки, чтобы ответы звучали как вы.",
      },
      {
        title: "Подключите канал",
        desc: "Добавьте виджет на сайт или подключите Telegram-канал.",
      },
      {
        title: "Получайте лиды",
        desc: "Посетители общаются, вы получаете чистые квалифицированные лиды.",
      },
    ],
  },
  features: {
    title: "Все возможности",
    subtitle: "AI-ассистент общается с клиентами и передаёт вам готовые заявки.",
    items: [
      {
        title: "Автоматический сбор лидов",
        desc: "Бот собирает имя, телефон и email во время разговора — лиды сразу попадают в вашу панель.",
      },
      {
        title: "Ответы из базы знаний",
        desc: "Загрузите документы, и бот будет отвечать клиентам на основе ваших реальных товаров и услуг.",
      },
      {
        title: "Работает на сайте и в Telegram",
        desc: "Установите виджет на сайт или подключите Telegram-бот — управляйте всем из одного места.",
      },
      {
        title: "Запуск за несколько минут",
        desc: "Выберите тип бизнеса, настройте стиль, и бот готов к работе — разработчики не нужны.",
      },
    ],
  },
  niches: {
    title: "Для Вашей Ниши",
    subtitle: "Выберите отправную точку — тон и процессы соответствуют вашей работе.",
    loading: "Загрузка...",
  },
  pricing: {
    title: "Простые, Прозрачные Цены",
    subtitle: "Начните бесплатно. Обновляйтесь по мере роста.",
    perMonth: "/ мес",
    popular: "Самый Популярный",
    free: "Бесплатно",
    plans: {
      free: {
        name: "Бесплатный",
        price: "0",
        desc: "Попробуйте Phoenix AI без обязательств",
        cta: "Начать бесплатно",
        features: [
          "1 бот",
          "100 разговоров/месяц",
          "Виджет для сайта",
          "1 PDF-документ",
          "Брендинг Phoenix AI",
          "Поддержка сообщества",
        ],
      },
      pro: {
        name: "Про",
        price: "39",
        desc: "Для бизнеса, готового собирать лиды в масштабе",
        cta: "Получить Про",
        features: [
          "5 ботов",
          "5 000 разговоров/месяц",
          "Сайт + Telegram",
          "25 PDF-документов",
          "Убрать брендинг",
          "Панель аналитики",
          "Email-поддержка",
        ],
      },
      business: {
        name: "Бизнес",
        price: "99",
        desc: "Для команд, которым нужна полная мощность",
        cta: "Получить Бизнес",
        features: [
          "Безлимитные боты",
          "20 000 разговоров/месяц",
          "Все каналы",
          "Безлимитные документы",
          "Доступ к API",
          "5 участников команды",
          "Расширенная аналитика",
          "Приоритетная поддержка",
        ],
      },
      enterprise: {
        name: "Корпоративный",
        price: "Связаться",
        desc: "Индивидуальный объём, SLA и персональная поддержка",
        cta: "Связаться",
        features: [
          "Всё из Бизнес",
          "Безлимитные разговоры",
          "Индивидуальный SLA",
          "Персональный менеджер",
          "Кастомные интеграции",
          "On-premise вариант",
        ],
      },
    },
  },
  faq: {
    title: "Часто задаваемые вопросы",
    subtitle: "Ответы на самые частые вопросы наших клиентов.",
    items: [
      {
        q: "Откуда бот знает, что отвечать моим клиентам?",
        a: "Вы загружаете свои документы (прайсы, описания услуг, FAQ), и бот учится по ним. Он отвечает только на основе ваших реальных данных, а не общими фразами.",
      },
      {
        q: "Что происходит, если бот не может ответить на вопрос?",
        a: "Бот вежливо сообщает клиенту, что передаст вопрос живому сотруднику, а разговор помечается в панели — вы сможете связаться позже.",
      },
      {
        q: "Могу ли я видеть разговоры и собранные лиды?",
        a: "Да. Каждый разговор, собранный контакт и лид отображаются в панели в реальном времени. Можно фильтровать, экспортировать и отслеживать всё.",
      },
      {
        q: "Как установить бот на мой сайт?",
        a: "Скопируйте одну строку кода и вставьте на сайт. Работает с любым конструктором — WordPress, Tilda, Wix или обычный HTML. Занимает менее 2 минут.",
      },
      {
        q: "Бот работает на нескольких языках?",
        a: "Да. Бот автоматически определяет язык посетителя и отвечает на нём. Поддерживаются английский, русский, узбекский, турецкий, арабский и многие другие.",
      },
      {
        q: "Можно ли попробовать бесплатно?",
        a: "Конечно. Бесплатный план даёт 1 бота и 100 разговоров в месяц — без привязки карты. Обновляйте тариф, когда потребуется больше.",
      },
      {
        q: "Данные моих клиентов в безопасности?",
        a: "Все данные шифруются при передаче и хранении. Мы не продаём ваши данные и не используем их для обучения AI. Вы можете удалить все данные в любой момент.",
      },
    ],
  },
  cta: {
    title: "Готовы получать больше лидов?",
    subtitle: "Сотни компаний уже используют Phoenix AI.",
    button: "Создать Бесплатный Аккаунт",
  },
  footer: {
    tagline: "AI-чатботы, которые превращают посетителей в реальных клиентов.",
    rights: "Все права защищены.",
    contact: "Контакты",
    terms: "Условия",
    privacy: "Конфиденциальность",
    product: "Продукт",
    legal: "Правовая информация",
  },
  auth: {
    login: {
      title: "Добро Пожаловать",
      subtitle: "Войдите в ваше рабочее пространство Phoenix AI.",
      email: "Email",
      password: "Пароль",
      submit: "Войти",
      submitting: "Вход...",
      forgotPassword: "Забыли пароль?",
      noAccount: "Нет аккаунта?",
      createOne: "Создать",
    },
    signup: {
      title: "Создать Аккаунт",
      subtitle: "Начните создавать с Phoenix AI.",
      name: "Полное имя",
      nameOptional: "(необязательно)",
      email: "Email",
      password: "Пароль",
      confirmPassword: "Подтвердите Пароль",
      submit: "Создать Аккаунт",
      submitting: "Создание аккаунта...",
      haveAccount: "Уже есть аккаунт?",
      signIn: "Войти",
    },
    forgotPassword: {
      title: "Восстановление Пароля",
      subtitle: "Введите email и мы отправим ссылку для сброса.",
      email: "Email",
      submit: "Отправить Ссылку",
      submitting: "Отправляем...",
      success:
        "Проверьте почту — если email зарегистрирован, мы отправили ссылку.",
      backToLogin: "Вернуться к входу",
    },
    resetPassword: {
      title: "Установить Новый Пароль",
      subtitle: "Выберите надёжный пароль для аккаунта.",
      password: "Новый Пароль",
      confirmPassword: "Подтвердите Пароль",
      submit: "Сбросить Пароль",
      submitting: "Сброс...",
      success: "Пароль обновлён! Теперь можно войти.",
    },
    verify: {
      title: "Подтвердите Email",
      subtitle: "Проверьте почту — мы отправили ссылку для подтверждения.",
      success: "Email подтверждён! Перенаправление...",
      invalid: "Ссылка недействительна или устарела.",
      resend: "Отправить письмо повторно",
    },
    oauth: {
      google: "Войти через Google",
      github: "Войти через GitHub",
      working: "Завершение входа...",
    },
    showPassword: "Показать пароль",
    hidePassword: "Скрыть пароль",
  },
  dashboard: {
    nav: {
      overview: "Обзор",
      businessPlan: "Бизнес-план",
      bots: "Боты",
      leads: "Лиды",
      knowledge: "База знаний",
      channels: "Каналы",
      analytics: "Аналитика",
      billing: "Тарифы",
      settings: "Настройки",
      marketingSite: "← Сайт",
    },
    topbar: {
      profile: "Профиль",
      settings: "Настройки",
      billing: "Тарифы",
      logout: "Выйти",
    },
    overview: {
      title: "Панель управления",
      subtitle: "Обзор рабочего пространства",
      hi: "Привет",
      hiAnon: "Добро пожаловать",
      welcomeLead: "Обзор вашего рабочего пространства. Создайте бота, загрузите знания и подключите канал, чтобы начать собирать лиды.",
      suggestedSteps: "С чего начать",
      step1: "Создайте первого бота и настройте его тон и поведение.",
      step2: "Загрузите документы, чтобы бот давал точные ответы.",
      step3: "Подключите виджет на сайт или Telegram, чтобы начать работу.",
      quickActions: "Быстрые действия",
      createBot: "Создать бота",
      createBotHint: "Настройте тон, промпты и поведение.",
      uploadKnowledge: "Загрузить знания",
      uploadKnowledgeHint: "Добавьте PDF, заметки или FAQ для бота.",
      connectChannel: "Подключить канал",
      connectChannelHint: "Виджет для сайта, Telegram или другие интеграции.",
      activity: "Ваша активность",
      open: "Смотреть все",
      recentBots: "Последние боты",
      recentBotsEmpty: "Пока нет ботов",
      recentBotsEmptyHint: "Создайте первого бота — он появится здесь.",
      recentLeads: "Последние лиды",
      recentLeadsEmpty: "Пока нет лидов",
      recentLeadsEmptyHint: "Лиды появятся здесь, когда посетители начнут общаться с вашим ботом.",
      channelStatus: "Каналы",
      channelStatusEmpty: "Нет подключённых каналов",
      channelStatusEmptyHint: "Подключите виджет или Telegram, чтобы получать сообщения.",
      createFirst: "Создайте первого бота",
      createFirstBody: "У вас пока нет ботов. Начать можно за одну минуту.",
      createFirstBtn: "Создать бота",
    },
    leads: {
      title: "Лиды",
      subtitle: "Потенциальные клиенты, собранные через ботов — статус, температура и контакты.",
      count: "лидов",
      countOne: "лид",
      filtered: "(отфильтровано)",
      showing: "Показано",
      pipelineStatus: "Этап воронки",
      allStages: "Все этапы",
      stNew: "Новый",
      stContacted: "Связались",
      stQualified: "Квалифицирован",
      stProposal: "Предложение",
      stWon: "Выигран",
      stLost: "Потерян",
      temperature: "Температура",
      anyTemp: "Любая температура",
      tempCold: "Холодный",
      tempWarm: "Тёплый",
      tempHot: "Горячий",
      nicheId: "Ниша",
      nichePlaceholder: "напр. образование",
      toolbarHint: "Фильтры запрашивают API в реальном времени.",
      colLead: "Лид",
      colStatus: "Статус",
      colTemp: "Темп.",
      colScore: "Балл",
      colNiche: "Ниша",
      colPhone: "Телефон",
      colCreated: "Создан",
      loadMore: "Загрузить ещё",
      loadingMore: "Загрузка...",
      emptyTitle: "Пока нет лидов",
      emptyBody: "Когда посетители начнут общаться с ботами, квалифицированные лиды появятся здесь.",
      emptyCta: "Перейти к ботам",
      emptyFilterTitle: "Нет лидов по этим фильтрам",
      emptyFilterBody: "Попробуйте сбросить этап, температуру или нишу, чтобы увидеть больше результатов.",
      emptyApiTitle: "API лидов недоступен",
      emptyApiBody: "Когда бэкенд будет развёрнут, собранные лиды появятся здесь автоматически.",
      retry: "Повторить",
      statsTotal: "Всего",
      statsNew: "Новые",
      statsQualified: "Квалифиц.",
      statsWon: "Выиграны",
      statsLost: "Потеряны",
      statsCold: "Холодные",
      statsWarm: "Тёплые",
      statsHot: "Горячие",
      detailBack: "Лиды",
      detailSummary: "Сводка",
      detailSummaryEmpty: "Для этого лида сводка не зафиксирована.",
      detailCollected: "Собранные данные",
      detailCollectedEmpty: "Структурированные поля не сохранены.",
      detailDetails: "Подробности",
      detailCurrentStatus: "Текущий статус",
      detailPhone: "Телефон",
      detailSource: "Источник",
      detailCreated: "Создан",
      detailUpdated: "Обновлён",
      detailPipeline: "Воронка и заметки",
      detailPipelineHint: "Выигран и потерян — финальные статусы. После них можно менять только температуру и заметки.",
      detailNoTemp: "Без температуры",
      detailNotes: "Внутренние заметки",
      detailNotesPlaceholder: "Итоги звонка, следующие шаги...",
      detailAssignee: "ID ответственного (UUID)",
      detailSaving: "Сохранение...",
      detailSave: "Сохранить изменения",
      detailLoadError: "Не удалось загрузить лид.",
      detailLoading: "Загрузка лида...",
    },
    botDetail: {
      tabSettings: "Настройки и чат",
      tabKnowledge: "База знаний",
      tabWidget: "Веб-виджет",
      tabTelegram: "Telegram",
      subtitle: "Детали бота, база знаний и тестовый чат",
      backToBots: "Назад к ботам",
      loadingBot: "Загрузка деталей бота...",
      loadError: "Не удалось загрузить детали бота.",
      retry: "Повторить",
      niche: "Ниша",
      goal: "Цель",
      currentStatus: "Текущий статус",
      lastUpdated: "Последнее обновление",
      name: "Имя",
      status: "Статус",
      tone: "Тон",
      language: "Язык",
      welcomeMessage: "Приветственное сообщение",
      shortDescription: "Краткое описание",
      statusDraft: "Черновик",
      statusActive: "Активный",
      statusPaused: "Приостановлен",
      statusArchived: "Архивирован",
      tonePlaceholder: "Дружелюбный и краткий",
      languagePlaceholder: "ru",
      welcomePlaceholder: "Здравствуйте! Чем могу помочь?",
      shortDescPlaceholder: "Опишите, чем занимается этот бот.",
      modelPlaceholder: "Оставьте пустым для значения по умолчанию",
      defaultPlaceholder: "По умолчанию",
      aiResponseTitle: "Ответ ИИ",
      aiResponseHint: "Необязательная настройка ответов. Оставьте поля пустыми для значений по умолчанию.",
      inferenceProvider: "Провайдер вывода",
      inferenceProviderHint: "Управляется платформой для этого рабочего пространства.",
      model: "Модель",
      modelHint: "Идентификатор модели провайдера (буквы, цифры, точки, подчёркивания, дефисы).",
      temperature: "Температура",
      temperatureHint: "0 = точнее, 2 = разнообразнее. Пусто = по умолчанию.",
      maxTokens: "Макс. выходных токенов",
      maxTokensHint: "Ограничивает длину ответа. Пусто = по умолчанию.",
      temperatureInvalid: "Температура должна быть числом от 0 до 2 или пустой для значения по умолчанию.",
      maxTokensInvalid: "Макс. токенов должно быть целым числом от 1 до 8192 или пустым.",
      archiveConfirmText: "Архивировать этого бота? Он останется в списке со статусом «архивирован».",
      archiving: "Архивация...",
      confirmArchive: "Подтвердить архивацию",
      cancel: "Отмена",
      saving: "Сохранение...",
      saveChanges: "Сохранить изменения",
      alreadyArchived: "Уже архивирован",
      archiveBot: "Архивировать бота",
      deletePermanently: "Удалить навсегда",
      deleteConfirmText: "Удалить этого бота навсегда? Это действие необратимо. Все связанные данные (база знаний, диалоги, лиды) будут удалены.",
      deleting: "Удаление...",
      confirmDelete: "Подтвердить удаление",
      testChatArchived: "Тестовый чат недоступен, пока бот архивирован.",
    },
    botTelegram: {
      lead: "Позвольте клиентам общаться с этим ботом в Telegram. Сообщения используют ту же конфигурацию ИИ, что и тестовый чат и веб-виджет.",
      loading: "Загрузка настроек Telegram…",
      loadError: "Не удалось загрузить настройки Telegram.",
      retry: "Повторить",
      upgradeTitle: "Интеграция с Telegram требует тарифа Pro или выше.",
      upgradeDesc: "Обновите тариф, чтобы подключить бота к Telegram и общаться с клиентами в их любимом мессенджере.",
      upgradeBtn: "Обновить тариф",
      botfatherTitle: "Токен BotFather",
      botfatherIntro: " — В Telegram откройте ",
      botfatherRun: ", запустите ",
      botfatherSelect: " или выберите бота, затем скопируйте ",
      apiToken: "API-токен",
      botfatherFormat: " (формат ",
      botfatherPaste: "). Вставьте его ниже один раз; мы проверим его в Telegram, зашифруем и ",
      neverShow: "больше никогда не покажем",
      botfatherEnd: " в этом интерфейсе.",
      connectionTitle: "Подключение",
      pillActive: "Активный",
      pillValidationFailed: "Проверка не пройдена",
      pillSetupInProgress: "Настройка выполняется",
      pillNotStarted: "Не начато",
      webhookRegistered: "Webhook зарегистрирован",
      botUsernamePrefix: "Имя пользователя бота: ",
      usernameAfterConfirm: "Имя пользователя появится здесь после подтверждения бота в Telegram.",
      usernameConnect: "Подключитесь, чтобы увидеть имя пользователя бота в Telegram.",
      lastVerifiedPrefix: "Последняя проверка: ",
      archivedNotice: "Этот бот архивирован. Действия подключения и токена отключены. Отключение по-прежнему доступно для удаления сохранённых данных.",
      lastIssuePrefix: "Последняя проблема: ",
      botTokenLabel: "Токен бота",
      botTokenHint: "Однократный ввод. После успешного подключения очистите поле сами или мы очистим его при успехе — API не возвращает секрет.",
      tokenPlaceholderStored: "Токен сохранён — вставьте только для замены (подключите снова)",
      tokenPlaceholderEmpty: "Вставьте токен из BotFather",
      connecting: "Подключение…",
      updateConnection: "Обновить подключение",
      connectTelegram: "Подключить Telegram",
      disconnecting: "Отключение…",
      disconnect: "Отключить",
    },
    botWidget: {
      lead: "Добавьте чат-виджет на свой сайт. Настройки применяются к публичному встраиванию; секретные ключи остаются на сервере.",
      loading: "Загрузка настроек виджета…",
      loadError: "Не удалось загрузить настройки виджета.",
      retry: "Повторить",
      settingsTitle: "Настройки виджета",
      settingsHint: "Разрешённые домены ограничивают, какие сайты могут загружать этот виджет. Оставьте пустым, чтобы разрешить любой источник при тестировании — ограничьте перед запуском.",
      enabledTitle: "Виджет включён",
      enabledMeta: "Когда выключено, посетители не могут загрузить виджет или общаться.",
      allowedDomains: "Разрешённые домены",
      domainsHint: "По одному хосту на строку. Порты не поддерживаются — используйте только хост.",
      welcomeLabel: "Приветственный текст виджета",
      welcomePlaceholder: "Показывается при открытии чата. Оставьте пустым для значения бота по умолчанию.",
      themeLabel: "Тема",
      themeAuto: "Авто (от посетителя)",
      themeLight: "Светлая",
      themeDark: "Тёмная",
      themeHint: "Управляет оформлением виджета; встраивание учитывает это при следующей загрузке.",
      saving: "Сохранение…",
      saveBtn: "Сохранить настройки виджета",
      installTitle: "Установка",
      installHint: "Ваш публичный ключ виджета безопасно встраивать в HTML. Он разрешает чат только на одобренных вами доменах.",
      publicKeyLabel: "Публичный ключ виджета",
      checklistBuild: "Соберите бандл виджета из embed-пакета Phoenix AI",
      checklistHost: "Разместите этот файл на вашем CDN или статическом сервере",
      checklistHostSetPre: " и установите ",
      checklistHostSetPost: " в этом приложении, чтобы сниппет ниже использовал ваш URL.",
      checklistHostConfigured: " (URL скрипта настроен для этой панели).",
      checklistApiPre: "Установите ",
      checklistApiMid: " для этой панели, чтобы сниппет включал ваш реальный API-адрес (или замените ",
      checklistApiPost: " вручную).",
      embedSnippet: "Сниппет для встраивания",
      copySnippet: "Копировать сниппет",
      copied: "Скопировано в буфер обмена.",
      copyError: "Не удалось скопировать — выделите код или проверьте разрешения браузера.",
    },
    bots: {
      title: "Ваши боты",
      subtitle: "Создавайте и настраивайте ботов для ваших клиентов.",
      createBtn: "Создать бота",
      search: "Поиск",
      searchPlaceholder: "Поиск бота по названию...",
      status: "Статус",
      allStatuses: "Все статусы",
      statusDraft: "Черновик",
      statusActive: "Активный",
      statusPaused: "Остановлен",
      statusArchived: "В архиве",
      statusChannelPending: "Ожидает канал",
      toolbarHint: "Поиск по имени, нише или цели. Фильтр по статусу.",
      colName: "Название",
      colNiche: "Ниша",
      colGoal: "Цель",
      colStatus: "Статус",
      colUpdated: "Обновлён",
      colActions: "Действия",
      clone: "Копировать",
      cloning: "Копирование...",
      emptyTitle: "Пока нет ботов",
      emptyBody: "Создайте первого бота — настройте тон и промпты, добавьте знания, подключите канал.",
      emptyApiNote: "API ботов недоступен. Вы всё равно можете создать нового бота.",
      emptyCta: "Создать первого бота",
      retry: "Повторить",
      loading: "Загрузка ботов...",
    },
    analytics: {
      title: "Аналитика",
      subtitle: "Отслеживайте ботов, лидов и использование",
      period: "Период",
      periodDays: "д",
      loading: "Загрузка аналитики…",
      noData: "Нет данных",
      loadError: "Не удалось загрузить аналитику",
      totalBots: "Всего ботов",
      activeCount: "активных",
      totalLeads: "Всего лидов",
      lastDays: "за",
      hotLeads: "Горячие лиды",
      highIntent: "высокий интерес",
      wonLeads: "Выигранные",
      convRate: "конверсия",
      leadPipeline: "Воронка лидов",
      leadTemperature: "Температура лидов",
      botStatus: "Статус ботов",
      planUsage: "Тариф и расход",
      noLeadsYet: "Пока нет лидов",
      noBotsYet: "Пока нет ботов",
      createOne: "создать",
      stNew: "Новый",
      stContacted: "Связались",
      stQualified: "Квалифиц.",
      stProposal: "Предложение",
      stWon: "Выигран",
      stLost: "Потерян",
      tempHot: "Горячий",
      tempWarm: "Тёплый",
      tempCold: "Холодный",
      tempUnknown: "Неизвестно",
      botActive: "Активный",
      botDraft: "Черновик",
      botPaused: "Приостановлен",
      botArchived: "Архивирован",
      total: "всего",
      leads: "лидов",
      plan: "Тариф",
      conversationsMonth: "Разговоров за месяц",
      unlimited: "Безлимитно",
      of: "из",
      billingHint: "Полные лимиты и опции обновления на",
      billingLink: "странице оплаты",
    },
    billing: {
      title: "Оплата",
      subtitle: "Управляйте подпиской и лимитами тарифа",
      loading: "Загрузка данных оплаты…",
      loadError: "Не удалось загрузить данные оплаты",
      checkoutSuccess: "Подписка активирована. Добро пожаловать!",
      checkoutCanceled: "Оплата отменена. Тариф не изменён.",
      stripeNotConfigured: "Платёжная система ещё не настроена. Обратитесь в поддержку.",
      checkoutFailed: "Оплата не прошла",
      noStripeLinked: "Нет привязанного Stripe аккаунта. Сначала оформите платный тариф.",
      portalUnavailable: "Портал недоступен",
      currentPlan: "Текущий тариф",
      planLabel: "Тариф",
      perMonth: "/мес",
      activeSub: "Ваша активная подписка",
      renews: "Продление",
      convPerMonth: "Разговоров/мес",
      bots: "Боты",
      pdfFiles: "PDF файлы",
      storage: "Хранилище",
      unlimited: "Безлимитно",
      manageBilling: "Управление оплатой",
      opening: "Открывается…",
      availablePlans: "Доступные тарифы",
      mostPopular: "Самый популярный",
      free: "Бесплатно",
      currentPlanBtn: "Текущий тариф",
      contactSupport: "Связаться с поддержкой",
      upgrade: "Улучшить",
      redirecting: "Перенаправление…",
      manage: "Управлять",
      conversations: "разговоров",
      bot: "бот",
      storageUnit: "хранилище",
      statusActive: "Активна",
      statusTrialing: "Пробная",
      statusPastDue: "Просрочена",
      statusCanceled: "Отменена",
      statusExpired: "Истекла",
      contactUs: "Связаться",
    },
    settings: {
      title: "Настройки",
      subtitle: "Управление профилем, безопасностью и параметрами аккаунта",
      loading: "Загрузка...",
      // Профиль
      profile: "Профиль",
      emailVerified: "Email подтверждён",
      emailUnverified: "Email не подтверждён",
      active: "Активен",
      inactive: "Неактивен",
      userId: "ID пользователя",
      memberSince: "Дата регистрации",
      lastUpdated: "Последнее обновление",
      displayNamePlaceholder: "Отображаемое имя",
      saving: "Сохранение...",
      save: "Сохранить",
      cancel: "Отмена",
      editDisplayName: "Изменить имя",
      nameUpdated: "Отображаемое имя обновлено.",
      // Безопасность аккаунта
      accountSecurity: "Безопасность аккаунта",
      emailVerifiedMsg: "Ваш email адрес подтверждён.",
      emailUnverifiedMsg: "Ваш email ещё не подтверждён. Подтвердите его для доступа ко всем функциям.",
      sending: "Отправка...",
      resendVerification: "Повторно отправить письмо",
      changePasswordHint: "Введите текущий пароль и выберите новый (минимум 8 символов).",
      changePassword: "Сменить пароль",
      passwordResetSent: "Ссылка для сброса пароля отправлена — проверьте почту.",
      currentPassword: "Текущий пароль",
      newPassword: "Новый пароль",
      confirmNewPassword: "Подтвердите новый пароль",
      passwordsDoNotMatch: "Пароли не совпадают",
      passwordTooShort: "Пароль должен содержать не менее 8 символов",
      passwordChanged: "Пароль успешно изменён!",
      changingPassword: "Изменение...",
      wrongCurrentPassword: "Текущий пароль неверен",
      verificationSent: "Письмо отправлено — проверьте почту.",
      // 2FA
      twoFactor: "Двухфакторная аутентификация",
      twoFactorActivated: "Двухфакторная аутентификация активирована!",
      twoFactorDisableConfirm: "Вы уверены, что хотите отключить двухфакторную аутентификацию?",
      twoFactorDisabled: "Двухфакторная аутентификация отключена.",
      twoFactorProtected: "Ваш аккаунт защищён с помощью TOTP.",
      disable2fa: "Отключить 2FA",
      disabling: "Отключение...",
      scanQrCode: "Отсканируйте QR-код приложением-аутентификатором (Google Authenticator, Authy и др.), затем введите код ниже.",
      manualEntryKey: "Ключ для ручного ввода:",
      recoveryCodes: "Коды восстановления (сохраните надёжно):",
      totpPlaceholder: "6-значный код",
      verifying: "Проверка...",
      activate: "Активировать",
      twoFactorDesc: "Добавьте дополнительный уровень безопасности, включив двухфакторную аутентификацию через приложение.",
      settingUp: "Настройка...",
      setUp2fa: "Настроить 2FA",
      // Сессии
      activeSessions: "Активные сессии",
      loadingSessions: "Загрузка сессий...",
      noSessions: "Активные сессии не найдены.",
      started: "Начата",
      lastUsed: "Последнее использование",
      // Рабочее пространство
      workspace: "Рабочее пространство",
      billingPlans: "Оплата и тарифы",
      manageBots: "Управление ботами",
      // Данные и конфиденциальность
      dataPrivacy: "Данные и конфиденциальность",
      exportDesc: "Экспортируйте JSON-копию данных аккаунта — профиль, боты, лиды и информация о подписке.",
      exporting: "Экспорт...",
      exportData: "Экспорт моих данных",
      exportSuccess: "Данные успешно экспортированы.",
      // Опасная зона
      dangerZone: "Опасная зона",
      logoutAllDesc: "Выход со всех устройств немедленно аннулирует все активные сессии, включая текущую. Вы будете перенаправлены на страницу входа.",
      signingOut: "Выход...",
      signOutAll: "Выйти со всех устройств",
      logoutAllConfirm: "Все сессии будут завершены. Продолжить?",
      deleteAccountDesc: "Безвозвратное удаление аккаунта и всех данных (боты, разговоры, лиды, файлы).",
      cannotBeUndone: "нельзя отменить",
      absolutelySure: "Вы абсолютно уверены?",
      deleting: "Удаление...",
      yesDelete: "Да, удалить мой аккаунт",
      deleteAccount: "Удалить аккаунт",
      // Привязка Telegram
      telegramTitle: "Уведомления в Telegram",
      telegramDesc: "Привяжите Telegram-аккаунт, чтобы мгновенно получать оповещения о новых лидах от ваших ботов.",
      telegramLink: "Привязать Telegram",
      telegramLinkedMsg: "Ваш Telegram-аккаунт привязан. Уведомления о лидах будут приходить в ваш Telegram-чат.",
      telegramLinkedAt: "Привязан",
      telegramConnected: "Подключён",
      telegramUnlink: "Отвязать Telegram",
      telegramUnlinking: "Отвязка...",
      telegramNotConfigured: "Telegram-уведомления ещё не настроены для этой платформы. Обратитесь в поддержку за подробностями.",
    },
    notifications: {
      title: "Уведомления",
      bell: "Уведомления",
      empty: "Уведомлений пока нет",
      markAllRead: "Отметить все как прочитанные",
    },
    wizard: {
      title: "Создать бота",
      lead: "Несколько быстрых шагов — по одному экрану за раз. Ваш прогресс сохраняется автоматически на этом устройстве (токены Telegram никогда не сохраняются в браузере).",
      assistiveHint: "Используйте Продолжить для перехода вперёд и Назад для просмотра предыдущих выборов.",
      loading: "Загрузка сохранённого прогресса...",
      step: "Шаг",
      of: "из",
      back: "Назад",
      continue: "Продолжить",
      exitToBots: "К списку ботов",
      skipForNow: "Пропустить",
      createBot: "Создать бота",
      creatingBot: "Создание бота...",
      stepNiche: "Ниша",
      stepGoal: "Цель",
      stepBasics: "Основы",
      stepChannel: "Канал",
      stepKnowledge: "Знания",
      stepReview: "Обзор",
      nicheTitle: "Для чего этот бот?",
      nicheDesc: "Выберите контекст, который лучше всего подходит вашему бизнесу. Вы сможете уточнить позже.",
      goalTitle: "Что должен достигать бот?",
      goalDesc: "Выберите основной результат — тон и процессы будут соответствовать.",
      basicsTitle: "Имя и голос",
      basicsDesc: "Дайте боту понятное имя и определите, как он должен звучать для посетителей.",
      channelTitle: "Где люди будут с вами общаться",
      channelDesc: "Виджет для сайта работает без токена Telegram. Для Telegram (или обоих) нужен действующий токен BotFather.",
      knowledgeTitle: "Основывайте ответы на вашем контенте",
      knowledgeDesc: "Загрузите PDF-файлы и добавьте заметки, чтобы дать боту надёжный бизнес-контекст.",
      reviewTitle: "Проверка и создание",
      reviewDesc: "Подтвердите ваш выбор. Статус соответствует реальным правилам бэкенда.",
      nicheLoading: "Загрузка поддерживаемых ниш...",
      nicheLegend: "Ниша",
      nicheFallback: "Не удалось обновить список ниш с сервера. Показаны сохранённые значения — проверьте подключение.",
      goalLegend: "Цель",
      goalSupport: "Поддержка",
      goalSupportHint: "Быстрое решение проблем с помощью пошагового устранения и эскалации.",
      goalSales: "Продажи",
      goalSalesHint: "Конвертация посетителей в лиды с квалификацией и дальнейшими шагами.",
      goalFaq: "Частые вопросы",
      goalFaqHint: "Ответы на распространённые вопросы кратко и достоверно.",
      goalConsulting: "Консалтинг",
      goalConsultingHint: "Сбор контекста и предоставление экспертных рекомендаций.",
      botName: "Имя бота",
      botNameHelp: "Отображается в вашем рабочем пространстве и настройках каналов.",
      botNamePlaceholder: "напр. Помощник Магазина",
      toneLegend: "Тон",
      toneHelp: "Тон необязателен. Можно оставить пустым и настроить позже.",
      toneFriendly: "Дружелюбный и краткий",
      toneProfessional: "Профессиональный и формальный",
      tonePlayful: "Игривый и лёгкий",
      toneNeutral: "Нейтральный и фактический",
      languageLabel: "Язык",
      languageHelp: "Сохраняется в черновике и будет связан с многоязычным поведением, когда бэкенд будет готов.",
      shortDesc: "Краткое описание",
      shortDescPlaceholder: "напр. Помогает новым клиентам выбрать тариф и отвечает на вопросы.",
      openingLine: "Приветственное сообщение",
      openingLineHelp: "Оставьте пустым, чтобы использовать предложенное по умолчанию для вашей ниши и языка.",
      defaultWelcome: "Привет! Я могу помочь с заказами или вопросами о продуктах.",
      optional: "(необязательно)",
      channelHint: "Виджет для сайта не требует токена Telegram. Если вы выберете Telegram или Оба, бэкенд отметит бота активным только после валидного токена BotFather и успешной регистрации вебхука.",
      channelLegend: "Канал",
      chWebsite: "Виджет для сайта",
      chWebsiteHint: "Токен Telegram не требуется — бот может быть активен для веб-канала.",
      chTelegram: "Telegram",
      chTelegramHint: "Для активации бота требуется действующий токен BotFather.",
      chBoth: "Оба",
      chBothHint: "Веб может быть активен; для Telegram нужен проверенный токен и вебхук.",
      proPlus: "Pro+",
      upgradeForTelegram: "Для использования Telegram перейдите на Pro или выше.",
      telegramRequiresPro: "Для Telegram требуется тариф Pro или выше.",
      upgradeNow: "Улучшить тариф",
      telegramToken: "Токен Telegram-бота",
      telegramTokenHelp: "От BotFather. Если пропустите, бот будет создан со статусом «канал ожидает» — не активен, пока не подключите Telegram в настройках бота.",
      telegramTokenPlaceholder: "Вставьте токен для запуска в Telegram",
      channelPending: "канал ожидает",
      knowledgeHint: "База знаний даёт боту надёжный бизнес-контекст. Загрузите PDF-файлы прямо здесь — они будут отправлены на сервер автоматически после создания бота.",
      typicalSources: "Типичные источники",
      srcPdf: "PDF-документы",
      srcFaq: "Документы FAQ",
      srcService: "Информация об услугах",
      srcPricing: "Информация о ценах",
      pdfLiveTitle: "PDF хранятся на странице бота",
      pdfLiveBody: "После создания бота откройте его из Ботов и используйте Базу знаний.",
      notesLabel: "Заметки",
      notesHelp: "Добавьте URL или ключевые факты сейчас, если хотите. Пустое поле не помешает созданию.",
      notesPlaceholder: "напр. URL страницы цен, основные пункты политики возврата...",
      uploadDropTitle: "Перетащите PDF-файлы сюда или нажмите для выбора",
      uploadDropMeta: "Только PDF · Макс. 20 МБ на файл",
      removeFile: "Удалить",
      fileTooLarge: "Файл слишком большой (макс. 20 МБ)",
      fileNotPdf: "Принимаются только PDF-файлы",
      pendingUploadNote: "Файлы будут загружены автоматически после создания бота",
      revFiles: "PDF-файлы",
      noFilesAttached: "Файлы не прикреплены",
      filesReady: "файл(ов) готово к загрузке",
      uploadingFiles: "Загрузка файлов знаний...",
      uploadComplete: "Все файлы успешно загружены!",
      uploadPartialFail: "Некоторые файлы не удалось загрузить",
      revNiche: "Ниша",
      revGoal: "Цель",
      revName: "Имя",
      revLanguage: "Язык",
      revTone: "Тон",
      revChannel: "Канал",
      revTelegramToken: "Токен Telegram",
      revKnowledge: "Заметки к знаниям",
      tokenNA: "Не применимо",
      tokenProvided: "Указан (проверяется на сервере)",
      tokenNotProvided: "Не указан — ожидается статус «канал ожидает»",
      knowledgeSkipped: "Пропущено",
      knowledgeNone: "Нет (загрузите файлы после создания)",
      expectedStatus: "Ожидаемый статус рабочего пространства",
      outcomeActiveWeb: "Активен (веб)",
      outcomeActiveWebDetail: "Токен Telegram не требуется. Бот может работать через виджет на сайте.",
      outcomeActiveTg: "Активен (если Telegram примет токен)",
      outcomeActiveTgDetail: "Мы проверяем токен и регистрируем вебхук на сервере.",
      outcomePending: "Канал ожидает",
      outcomePendingDetail: "Сохранён без токена Telegram. Завершите настройку из панели Telegram бота.",
      outcomeDraft: "Черновик",
      outcomeDraftDetail: "Выберите канал, чтобы увидеть результат.",
      doneActiveTitle: "Бот сохранён и активен",
      doneActiveBody: "Статус рабочего пространства соответствует серверу: бот активен для готовых каналов.",
      donePendingTitle: "Бот сохранён — настройка не завершена",
      donePendingBody: "Статус «канал ожидает» до подключения Telegram с валидным токеном и вебхуком.",
      doneDefaultTitle: "Бот сохранён",
      doneDefaultBody: "Переход к рабочему пространству ботов...",
      serverStatus: "Статус сервера:",
      primaryChannel: "основной канал:",
      openBots: "Открыть ботов",
    },
  },
  superadmin: {
    nav: {
      overview:     "Обзор Платформы",
      users:        "Пользователи",
      bots:         "Боты",
      billing:      "Биллинг",
      aiUsage:      "Использование ИИ",
      auditLog:     "Журнал аудита",
      featureFlags: "Флаги",
      support:      "Поддержка",
      coupons:      "Купоны",
      analytics:    "Сегмент Аналитика",
      abuse:        "Обнаружение Злоупотреблений",
      export:       "Экспорт Данных",
      campaigns:    "Email Рассылки",
      webhookLogs:  "Журнал Вебхуков",
    },
    common: {
      loading: "Загрузка...",
      error: "Ошибка",
      save: "Сохранить",
      saving: "Сохранение...",
      cancel: "Отмена",
      create: "Создать",
      edit: "Изменить",
      delete: "Удалить",
      deleting: "Удаление...",
      confirm: "Подтвердить",
      total: "Всего",
      noRecords: "Записей не найдено",
      actions: "Действия",
      status: "Статус",
      period: "Период",
      allStatuses: "Все статусы",
      allPlans: "Все планы",
      allTypes: "Все типы",
      allActions: "Все действия",
      clear: "Очистить",
      view: "Просмотр",
      back: "Назад",
    },
    flags: {
      total: "флагов",
      newFlag: "+ Новый флаг",
      key: "Ключ",
      state: "Состояние",
      plan: "План",
      description: "Описание",
      updated: "Обновлён",
      enabled: "Включён",
      disabled: "Выключен",
      toggleTitle: "Переключить",
      createTitle: "Создать флаг",
      editTitle: "Редактировать флаг",
      keyLabel: "Ключ *",
      keyHelp: "Только строчные буквы, цифры и _",
      keyPlaceholder: "напр. advanced_analytics",
      descLabel: "Описание (необязательно)",
      descPlaceholder: "Для чего этот флаг...",
      targetPlan: "Целевой план (необязательно)",
      globalAllPlans: "Глобально (все планы)",
      enableOnCreate: "Включить сразу",
      deleteTitle: "Удалить флаг",
      deleteConfirm: "Удалить флаг",
      deleteWarn: "Это действие нельзя отменить.",
      yesDelete: "Да, удалить",
      emptyState: "Флагов пока нет. Создайте новый флаг.",
      targetUsers: "Целевые пользователи",
      targetUsersHelp: "Введите email пользователей для включения флага",
      addEmail: "Добавить",
      emailPlaceholder: "user@example.com",
      usersTargeted: "пользователей",
      noUserTarget: "Нет таргетинга",
      invalidEmail: "Неверный формат email",
    },
    billing: {
      user: "Пользователь",
      plan: "План",
      periodStart: "Начало периода",
      periodEnd: "Конец периода",
      canceled: "Отменена",
      stripe: "Stripe",
      changePlan: "Сменить план",
      changePlanTitle: "Смена плана",
      newPlan: "Новый план",
      reason: "Причина (необязательно)",
      reasonPlaceholder: "Заметка администратора...",
      blocked: "Заблокирован",
      manual: "Вручную",
      free: "бесплатно",
      statusActive: "Активна",
      statusTrialing: "Пробный",
      statusPastDue: "Просрочен",
      statusCanceled: "Отменена",
      statusExpired: "Истёк",
      totalActive: "Всего активных",
      totalPastDue: "Просроченных",
      estimatedMrr: "Оценочный MRR",
      mrrNote: "На основе цен планов на текущей странице",
    },
    aiUsage: {
      periodLabel: "Период:",
      summaryTitle: "общий расход AI платформы",
      totalCalls: "Всего запросов",
      successful: "Успешных",
      failed: "Ошибок",
      successRate: "Успешность",
      totalTokens: "Всего токенов",
      totalCost: "Общая стоимость",
      dailyHistory: "История по дням",
      date: "Дата",
      calls: "Запросы",
      tokens: "Токены",
      costUsd: "Стоимость (USD)",
      topConsumers: "Топ потребителей токенов (Топ 10)",
      user: "Пользователь",
      cost: "Стоимость",
      noData: "Нет данных по расходу AI за этот период.",
    },
    auditLog: {
      time: "Время",
      action: "Действие",
      entityType: "Тип / Entity ID",
      actor: "Актор",
      meta: "Мета",
      snapshot: "Снимок",
      snapshotTitle: "Снимок",
      before: "До (before)",
      after: "После (after)",
      metadata: "Метаданные",
      sinceDate: "С даты",
    },
    export: {
      intro: "Экспорт данных платформы в CSV для отчётности, аудита и финансового анализа.",
      download: "Скачать",
      downloading: "Загрузка...",
      downloadFailed: "Не удалось скачать",
      usersLabel: "Пользователи",
      usersDesc: "Все зарегистрированные — ID, email, роль, статус, даты.",
      subscriptionsLabel: "Подписки",
      subscriptionsDesc: "Все подписки — план, статус, Stripe ID, периоды.",
      aiUsageLabel: "Расход AI",
      aiUsageDesc: "Дневной расход AI по ботам — запросы, токены, стоимость.",
      couponsLabel: "Купоны",
      couponsDesc: "Все коды купонов — скидки, использование, срок.",
      quickPresets: "Быстрые пресеты",
      preset7d: "Последние 7 дней",
      preset30d: "Последние 30 дней",
      preset90d: "Последние 90 дней",
      presetYtd: "С начала года",
    },
    overview: {
      intro: "Статистика платформы в реальном времени. Используйте боковую панель для просмотра пользователей, ботов и биллинга.",
      loadingOverview: "Загрузка...",
      usersAndBots: "Пользователи и Боты",
      registeredUsers: "Зарегистрированные",
      activeUsers: "Активные пользователи",
      totalBots: "Всего ботов",
      activeBots: "Активные боты",
      leads: "Лиды",
      conversations: "Разговоры",
      billingRevenue: "Биллинг и Доход",
      mrr: "MRR",
      mrrSub: "Ежемесячный регулярный доход",
      paidActive: "Платные активные",
      paidActiveSub: "Активные платные подписчики",
      freePlan: "Бесплатный план",
      freePlanSub: "На бесплатном тарифе",
      pastDue: "Просрочено",
      pastDueSub: "Платёж не прошёл",
      canceled: "Отменено",
      canceledSub: "Отток",
      planDistribution: "Распределение планов",
      generatedAt: "Сгенерировано",
      viewBilling: "Детали биллинга",
      planChart: "Распределение планов",
      autoRefresh: "Авто-обновление",
      refreshEvery: "Обновление каждые",
      seconds: "с",
      recentActivity: "Последняя активность",
    },
    users: {
      intro: "Все учётные записи. Откройте строку для деталей и модерации.",
      showingRange: "Показано",
      noUsers: "Нет пользователей",
      selected: "выбрано",
      suspend: "Заблокировать",
      activate: "Активировать",
      applyTo: "Применить к",
      previous: "Назад",
      next: "Вперёд",
      selectAll: "Выбрать все",
      email: "Email",
      role: "Роль",
      status: "Статус",
      bots: "Боты",
      updated: "Обновлено",
      inactive: "Неактивен",
      suspended: "Заблокирован",
      active: "Активен",
      confirmBulkTitle: "Подтверждение массового действия",
      confirmBulkHint: "Применить действие к выбранным?",
      reasonOptional: "Причина (необязательно)",
      reasonPlaceholder: "Причина блокировки...",
      processing: "Обработка...",
      confirmAction: "Подтвердить",
      bulkSuccess: "Массовое действие выполнено",
    },
    botsList: {
      intro: "Все боты. Откройте строку для настроек и модерации.",
      showingRange: "Показано",
      noBots: "Нет ботов",
      previous: "Назад",
      next: "Вперёд",
      bot: "Бот",
      owner: "Владелец",
      status: "Статус",
      channels: "Каналы",
      updated: "Обновлено",
      platformSuspended: "Заблокирован платформой",
      widget: "Виджет",
      telegram: "Telegram",
      selected: "выбрано",
      bulkSuspend: "Заблокировать выбранные",
      bulkActivate: "Активировать выбранные",
      bulkSuspendTitle: "Массовая блокировка ботов",
      bulkActivateTitle: "Массовая активация ботов",
      bulkApplyTo: "Действие будет применено к",
      botsCount: "ботам",
      bulkReason: "Причина (необязательно)",
      bulkReasonPlaceholder: "Напр.: Нарушение правил, спам...",
    },
    userDetail: {
      loadingUser: "Загрузка...",
      backToUsers: "К пользователям",
      inspectTenant: "Инспекция тенанта (только чтение, аудит)",
      email: "Email",
      name: "Имя",
      role: "Роль",
      active: "Активен",
      verified: "Верифицирован",
      password: "Пароль",
      suspendedAt: "Заблокирован",
      suspensionNote: "Причина блокировки",
      oauthProviders: "OAuth провайдеры",
      bots: "Боты",
      created: "Создан",
      updated: "Обновлён",
      yes: "Да",
      no: "Нет",
      set: "Установлен",
      notSet: "Не установлен",
      activateUser: "Активировать",
      cannotSuspendSelf: "Вы не можете заблокировать свой аккаунт из этой консоли.",
      suspendUser: "Заблокировать",
      impersonation: "Имперсонация",
      impersonationDesc: "Создать 15-минутный токен для просмотра аккаунта. Записывается в аудит.",
      generating: "Генерация...",
      generateToken: "Создать токен имперсонации",
      tokenHint: "Токен (15 мин) — скопируйте и используйте как Bearer:",
      copy: "Копировать",
      dismiss: "Закрыть",
      planOverride: "Смена плана",
      plan: "План",
      reasonOptional: "Причина (необязательно)",
      reasonPlaceholder: "Внутренняя причина...",
      applying: "Применение...",
      applyOverride: "Применить",
      userSuspended: "Пользователь заблокирован.",
      userActivated: "Пользователь активирован.",
      planOverridden: "План изменён.",
      suspendTitle: "Заблокировать пользователя",
      suspendDesc: "Аккаунт станет неактивным, вход будет заблокирован. Внутренняя заметка сохраняется для операторов.",
      suspendConfirm: "Заблокировать",
    },
    botDetail: {
      loadingBot: "Загрузка...",
      backToBots: "К ботам",
      name: "Название",
      botId: "ID бота",
      ownerEmail: "Email владельца",
      ownerId: "ID владельца",
      niche: "Ниша",
      goal: "Цель",
      status: "Статус",
      providerModel: "Провайдер / модель",
      widget: "Виджет",
      telegram: "Telegram",
      platformSuspended: "Заблокирован платформой",
      suspensionNote: "Причина блокировки",
      welcome: "Приветствие",
      tone: "Тон",
      language: "Язык",
      description: "Описание",
      temperature: "Температура",
      maxOutputTokens: "Макс. токенов",
      created: "Создан",
      updated: "Обновлён",
      configured: "Настроен",
      notConfigured: "Не настроен",
      connected: "Подключён",
      notConnected: "Не подключён",
      clearSuspension: "Снять блокировку",
      platformSuspendBot: "Заблокировать бота",
      botSuspended: "Бот заблокирован платформой.",
      suspensionCleared: "Блокировка снята.",
      suspendBotTitle: "Заблокировать бота",
      suspendBotDesc: "Блокирует виджет, Telegram ответы и тестовый чат для этого бота. Рабочее пространство владельца не меняется.",
      suspendBotConfirm: "Заблокировать",
      performance: "Производительность",
      conversations: "Диалоги",
      leadsGenerated: "Созданные лиды",
      aiCalls: "AI вызовы",
      aiTokens: "AI токены",
    },
    support: {
      loadError: "Не удалось загрузить тикеты.",
      updateError: "Не удалось обновить тикет.",
      allStatuses: "Все статусы",
      statusOpen: "Открыт",
      statusInProgress: "В работе",
      statusResolved: "Решён",
      statusClosed: "Закрыт",
      allPriorities: "Все приоритеты",
      priorityLow: "Низкий",
      priorityNormal: "Обычный",
      priorityHigh: "Высокий",
      ticketsCount: "тикетов",
      subject: "Тема",
      user: "Пользователь",
      status: "Статус",
      priority: "Приоритет",
      created: "Создан",
      actions: "Действия",
      noTickets: "Тикеты не найдены.",
      notePrefix: "Заметка:",
      edit: "Изменить",
      prevPage: "Назад",
      nextPage: "Вперёд",
      pageOf: "Страница",
      updateTitle: "Обновить тикет",
      statusLabel: "Статус",
      priorityLabel: "Приоритет",
      adminNote: "Заметка админа",
      notePlaceholder: "Оставьте заметку для тикета...",
      replyTitle: "Детали тикета",
      ticketBody: "Сообщение",
      replyLabel: "Ответ администратора",
      replyPlaceholder: "Напишите ответ...",
      replyAndProgress: "Ответить и взять в работу",
      replyAndResolve: "Ответить и решить",
      submittedAt: "Отправлено",
      resolvedAt: "Решено",
      noReplyYet: "Ответа пока нет",
      previousReply: "Предыдущий ответ",
      cancel: "Отмена",
      saving: "Сохранение...",
      save: "Сохранить",
    },
    abuse: {
      loadError: "Не удалось загрузить отчёт о злоупотреблениях.",
      suspendError: "Блокировка не удалась.",
      periodLabel: "Период (дни):",
      day1: "1 день",
      day3: "3 дня",
      day7: "7 дней",
      minCalls: "Мин. вызовов:",
      refresh: "Обновить",
      highUsageTitle: "Аккаунты с высоким расходом",
      user: "Пользователь",
      calls: "Вызовы",
      failed: "Ошибки",
      tokens: "Токены",
      cost: "Стоимость",
      errorRate: "Процент ошибок",
      actions: "Действия",
      noHighUsage: "Аккаунтов с высоким расходом не обнаружено.",
      suspend: "Заблокировать",
      topErrorsTitle: "Частые коды ошибок",
      errorCode: "Код ошибки",
      occurrences: "Количество",
      noErrors: "Нет данных об ошибках.",
      suspendedUser: "Заблокирован",
      failedToSuspend: "Не удалось заблокировать",
    },
    campaigns: {
      segmentAllUsers: "Все активные пользователи",
      segmentPastDue: "С просроченным платежом",
      segmentFreePlan: "Бесплатный план",
      segmentPaidUsers: "Платные пользователи",
      segmentInactive7d: "Неактивные 7+ дней",
      loadError: "Не удалось загрузить кампании.",
      createError: "Не удалось создать кампанию.",
      updateError: "Не удалось обновить кампанию.",
      sendError: "Не удалось отправить кампанию.",
      deleteError: "Не удалось удалить кампанию.",
      newCampaign: "+ Новая кампания",
      campaignsCount: "кампаний",
      subject: "Тема",
      segment: "Сегмент",
      status: "Статус",
      sentFailed: "Отправлено / Ошибки",
      sentAt: "Отправлено",
      actions: "Действия",
      noCampaigns: "Кампаний пока нет.",
      recipients: "получателей",
      failedCount: "ошибок",
      preview: "Предпросмотр",
      edit: "Изменить",
      send: "Отправить",
      delete: "Удалить",
      prevPage: "Назад",
      nextPage: "Вперёд",
      pageOf: "Страница",
      newTitle: "Новая email кампания",
      subjectLabel: "Тема",
      targetSegment: "Целевой сегмент",
      bodyLabel: "Текст (HTML)",
      cancel: "Отмена",
      creating: "Создание...",
      createDraft: "Создать черновик",
      editTitle: "Редактировать кампанию",
      bodyHtml: "Текст HTML",
      saving: "Сохранение...",
      saveChanges: "Сохранить",
      previewTitle: "Предпросмотр",
      segmentLabel: "Сегмент",
      close: "Закрыть",
      sendTitle: "Отправить кампанию?",
      sendConfirm: "Кампания будет отправлена немедленно. Это действие необратимо.",
      sending: "Отправка...",
      confirmSend: "Подтвердить отправку",
      deleteTitle: "Удалить кампанию?",
      deleteConfirm: "Вы уверены? Это действие необратимо.",
      deleting: "Удаление...",
      campaignCreated: "Кампания создана",
      campaignUpdated: "Кампания обновлена.",
      campaignSending: "Кампания отправляется",
      templateLabel: "Шаблон",
      tplBlank: "Пустой",
      tplBlankDesc: "Начать с нуля",
      tplWelcome: "Приветствие",
      tplWelcomeDesc: "Онбординг для новых пользователей",
      tplAnnouncement: "Объявление",
      tplAnnouncementDesc: "Обновление продукта или новость",
      tplPromotion: "Акция",
      tplPromotionDesc: "Скидка или специальное предложение",
      tplReengagement: "Реактивация",
      tplReengagementDesc: "Вернуть неактивных пользователей",
    },
    coupons: {
      loadError: "Не удалось загрузить купоны.",
      createError: "Не удалось создать купон.",
      updateError: "Не удалось обновить купон.",
      deleteError: "Не удалось удалить купон.",
      codeExists: "Код купона уже существует.",
      newCoupon: "+ Новый купон",
      couponsCount: "купонов",
      code: "Код",
      discount: "Скидка",
      plan: "План",
      uses: "Использования",
      expires: "Срок",
      status: "Статус",
      actions: "Действия",
      noCoupons: "Купонов пока нет.",
      allPlans: "все",
      active: "активен",
      inactive: "неактивен",
      edit: "Изменить",
      delete: "Удалить",
      createTitle: "Создать купон",
      codeLabel: "Код (заглавные, напр. LAUNCH50)",
      typeLabel: "Тип",
      valueLabel: "Значение",
      percentType: "Процент (%)",
      usdType: "USD ($)",
      targetPlan: "Целевой план (необязательно)",
      maxUses: "Макс. использований (необязательно)",
      expiresAt: "Срок действия (необязательно)",
      cancel: "Отмена",
      creating: "Создание...",
      create: "Создать",
      editTitle: "Редактирование",
      activeLabel: "Активен",
      inactiveLabel: "Неактивен",
      clearExpiry: "Убрать срок (бессрочный)",
      saving: "Сохранение...",
      save: "Сохранить",
      deleteTitle: "Удалить купон?",
      deleteConfirm: "Вы уверены, что хотите удалить этот купон? Это необратимо.",
      deleting: "Удаление...",
      couponCreated: "Купон создан.",
      analyticsActive: "Активные купоны",
      analyticsRedemptions: "Всего использований",
      analyticsExpired: "Истекшие",
      analyticsMaxedOut: "Исчерпанные",
      analyticsAvgDiscount: "Средняя скидка",
    },
    webhooks: {
      loadError: "Не удалось загрузить журнал вебхуков.",
      failedTotal: "неудачных вебхуков всего",
      showFailedOnly: "Только ошибки",
      allSources: "Все источники",
      stripe: "Stripe",
      telegram: "Telegram",
      allStatuses: "Все статусы",
      received: "Получен",
      processed: "Обработан",
      failed: "Ошибка",
      clearDates: "Сбросить даты",
      logsCount: "записей",
      source: "Источник",
      eventType: "Тип события",
      status: "Статус",
      bot: "Бот",
      receivedAt: "Получен",
      details: "Детали",
      noLogs: "Записей вебхуков не найдено.",
      view: "Просмотр",
      prevPage: "Назад",
      nextPage: "Вперёд",
      pageOf: "Страница",
      close: "Закрыть",
    },
    tenant: {
      loadingInspection: "Загрузка инспекции...",
      backToUser: "К пользователю",
      intro: "Операционный снимок (только чтение). Открытие создаёт запись в журнале аудита.",
      leads: "Лиды",
      conversations: "Разговоры",
      aiCalls: "AI вызовы",
      aiFailures: "AI ошибки",
      tokensWindow: "Токены",
      tenantSummary: "Сводка тенанта",
      email: "Email",
      role: "Роль",
      active: "Активен",
      botsProfile: "Боты (профиль)",
      yes: "Да",
      no: "Нет",
      channelMix: "Каналы (разговоры)",
      noConversations: "Разговоров пока нет.",
      channel: "Канал",
      botsShown: "Боты",
      noBotsForTenant: "У этого тенанта нет ботов.",
      bot: "Бот",
      status: "Статус",
      channels: "Каналы",
      widget: "Виджет",
      telegram: "Telegram",
      aiUsageWindow: "Окно AI расхода",
      dailyRollup: "Дневной AI расход (последние дни)",
      noDailyData: "Нет дневных данных за период.",
      date: "Дата",
      requests: "Запросы",
      tokens: "Токены",
      costUsd: "Стоимость (USD)",
      recentErrors: "Последние ошибки AI",
      noFailedCalls: "Нет неудачных AI вызовов для этого тенанта.",
      when: "Когда",
      model: "Модель",
      code: "Код",
    },
    analytics: {
      channelWebWidget: "Веб-виджет",
      channelTelegram: "Telegram",
      channelAdminTest: "Админ-тест",
      loadError: "Не удалось загрузить аналитику.",
      periodLabel: "Период: последние",
      channelDistribution: "Распределение каналов",
      noConversationData: "Данных о разговорах пока нет.",
      userSignups: "Регистрации пользователей",
      noSignupData: "Нет данных о регистрациях за этот период.",
      date: "Дата",
      newUsers: "Новые пользователи",
      bar: "График",
      planSegments: "Сегменты планов",
      plan: "План",
      status: "Статус",
      count: "Количество",
      churnByPlan: "Отток по планам",
      canceled: "Отменено",
      noChurnData: "Нет данных об оттоке.",
      botsByNiche: "Боты по нишам",
      niche: "Ниша",
      bots: "Боты",
      noData: "Нет данных.",
      botsByGoal: "Боты по типу цели",
      signupChart: "Тренд регистраций",
      channelChart: "Распределение каналов",
      goal: "Цель",
    },
    moderation: {
      internalNote: "Внутренняя заметка (необязательно)",
      internalNotePlaceholder: "Внутренняя заметка (необязательно, макс. 1024 символов)",
      cancel: "Отмена",
    },
  },
  common: {
    loading: "Загрузка...",
    error: "Что-то пошло не так",
    save: "Сохранить",
    cancel: "Отмена",
    delete: "Удалить",
    edit: "Редактировать",
    back: "Назад",
    next: "Далее",
    finish: "Завершить",
    optional: "необязательно",
    or: "или",
  },
};

export const translations: Record<Lang, Translations> = { en, uz, ru };
