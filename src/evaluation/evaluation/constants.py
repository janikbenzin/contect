from contect.available.available import AvailableClassifications

TRUE_LBL = 'true'
PRED_LBL = 'pred'
CMS_LBL = 'cms'
REPORT_LBL = 'reports'
B_ACC_LBL = 'balanced_accs'
ACC_LBL = 'accs'
R_ACC_LBL = 'raw_accs'
PERC_POS_LBL = 'perc_pos_attributable'
PERC_D_LBL = 'perc_deviating'
RECALL_LBL = 'recall'
R_RECALL_LBL = 'raw_recall'
PREC_LBL = 'precision'
R_PREC_LBL = 'raw_precision'
W_AVG_LBL = 'weighted avg'
D_N_CLASSES = [AvailableClassifications.D.value, AvailableClassifications.N.value]
CLASSES = [c.value for c in AvailableClassifications]
PERCS = [0, 0.25, 0.5, 0.75, 1]
DEVS = [0.02, 0.05, 0.10]
POST_PS = 'alpha_ps'
POST_NG = 'alpha_ng'
