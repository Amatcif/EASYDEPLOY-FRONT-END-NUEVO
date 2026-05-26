export const actionMap: Record<string, string> = {
  ad_dc1: 'ad.dc1',
  ad_dc2: 'ad.dc2',
  ad_join: 'ad.join_domain',
  ad_users: 'ad.create_users',
  ad_repadmin: 'ad.repadmin',
  ad_d2_d4: 'ad.d2d4',

  kms_run: 'kms.run',
  sharepoint_install: 'sharepoint.install',
  sql_2022: 'sql.install_2022',
  jchat_openfire: 'jchat.openfire',
  jchat_cli: 'jchat.cli',

  exchange_prereqs: 'exchange.prereqs',
  exchange_prepare_ad: 'exchange.prepare_schema',
  exchange_install: 'exchange.install',
  exchange_users: 'exchange.create_users',
  exchange_recover: 'exchange.recover_server',

  skype_prereqs: 'skype.prereqs',
  skype_install: 'skype.install',
  skype_perms: 'skype.permissions',
  skype_dns: 'skype.dns',

  netfx35: 'programs.netfx35',
  firefox: 'programs.firefox',
  winrar: 'programs.winrar',
  adobe_reader: 'programs.adobe_reader',
  office_skype: 'programs.office_skype',
  install_all: 'programs.install_all',

  tools_gpo_force: 'tools.gpo_force',

  network_allied: 'networks.switch_allied',
  network_cisco: 'networks.switch_cisco',
  network_router: 'networks.router',
  network_asa: 'networks.asa',
  network_checkpoint: 'networks.checkpoint',
  network_topology: 'networks.topology',
  network_ip: 'networks.ip_addressing',
};

export function realActionId(actionId: string) {
  return actionMap[actionId] || actionId;
}
