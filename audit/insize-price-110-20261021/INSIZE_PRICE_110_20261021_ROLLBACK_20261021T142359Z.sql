
BEGIN ISOLATION LEVEL SERIALIZABLE;

CREATE TEMP TABLE insize_p110_rollback_expected (
  product_id integer PRIMARY KEY,
  expected_sku text NOT NULL,
  restore_base_price numeric(12,2) NOT NULL,
  applied_base_price numeric(12,2) NOT NULL,
  restore_original_price numeric(12,2),
  clear_original_exception boolean NOT NULL DEFAULT FALSE
) ON COMMIT DROP;
INSERT INTO insize_p110_rollback_expected
  (product_id, expected_sku, restore_base_price, applied_base_price, restore_original_price, clear_original_exception)
VALUES
  (1771, '0110-1125', '31416000.00'::numeric, '34557600.00'::numeric, NULL, FALSE),
  (1772, '1103-150', '10791000.00'::numeric, '11870100.00'::numeric, NULL, FALSE),
  (1773, '1103-200', '15180000.00'::numeric, '16698000.00'::numeric, NULL, FALSE),
  (1774, '1103-300', '26697000.00'::numeric, '29366700.00'::numeric, NULL, FALSE),
  (1777, '1106-501', '52800000.00'::numeric, '58080000.00'::numeric, NULL, FALSE),
  (1785, '1108-150', '7854000.00'::numeric, '8639400.00'::numeric, NULL, FALSE),
  (1786, '1108-200', '11616000.00'::numeric, '12777600.00'::numeric, NULL, FALSE),
  (1787, '1108-300', '20823000.00'::numeric, '22905300.00'::numeric, NULL, FALSE),
  (1788, '1111-100', '9636000.00'::numeric, '10599600.00'::numeric, NULL, FALSE),
  (1789, '1114-150', '9405000.00'::numeric, '10345500.00'::numeric, NULL, FALSE),
  (1790, '1114-200', '12870000.00'::numeric, '14157000.00'::numeric, NULL, FALSE),
  (1791, '1114-300', '22440000.00'::numeric, '24684000.00'::numeric, NULL, FALSE),
  (1795, '1120-150', '24651000.00'::numeric, '27116100.00'::numeric, NULL, FALSE),
  (1810, '1141-150', '11715000.00'::numeric, '12886500.00'::numeric, NULL, FALSE),
  (1820, '1150-300', '70950000.00'::numeric, '78045000.00'::numeric, NULL, FALSE),
  (1821, '1150-500', '104940000.00'::numeric, '115434000.00'::numeric, NULL, FALSE),
  (1831, '1176-150', '60720000.00'::numeric, '66792000.00'::numeric, NULL, FALSE),
  (1841, '1196-300', '29568000.00'::numeric, '32524800.00'::numeric, NULL, FALSE),
  (1845, '1214-500', '36960000.00'::numeric, '40656000.00'::numeric, NULL, FALSE),
  (1846, '1214-600', '40590000.00'::numeric, '44649000.00'::numeric, NULL, FALSE),
  (1861, '1311-200', '16368000.00'::numeric, '18004800.00'::numeric, NULL, FALSE),
  (1862, '1311-300', '25608000.00'::numeric, '28168800.00'::numeric, NULL, FALSE),
  (1864, '1312-200', '15015000.00'::numeric, '16516500.00'::numeric, NULL, FALSE),
  (1865, '1312-300', '22275000.00'::numeric, '24502500.00'::numeric, NULL, FALSE),
  (1880, '2171-250', '16170000.00'::numeric, '17787000.00'::numeric, NULL, FALSE),
  (1886, '2176-300', '7788000.00'::numeric, '8566800.00'::numeric, NULL, FALSE),
  (1887, '2179-360', '17754000.00'::numeric, '19529400.00'::numeric, NULL, FALSE),
  (1890, '2275-300', '3085500.00'::numeric, '3394050.00'::numeric, NULL, FALSE),
  (1891, '2278-180', '22242000.00'::numeric, '24466200.00'::numeric, NULL, FALSE),
  (1894, '2322-160', '25080000.00'::numeric, '27588000.00'::numeric, NULL, FALSE),
  (1896, '2322-450', '39600000.00'::numeric, '43560000.00'::numeric, NULL, FALSE),
  (1901, '2372-360', '19404000.00'::numeric, '21344400.00'::numeric, NULL, FALSE),
  (1904, '2381-021', '22704000.00'::numeric, '24974400.00'::numeric, NULL, FALSE),
  (1910, '2828-800', '92070000.00'::numeric, '101277000.00'::numeric, NULL, FALSE),
  (1914, '2871-101', '41910000.00'::numeric, '46101000.00'::numeric, NULL, FALSE),
  (1941, '3203-100', '9372000.00'::numeric, '10309200.00'::numeric, NULL, FALSE),
  (1942, '3203-125', '12045000.00'::numeric, '13249500.00'::numeric, NULL, FALSE),
  (1943, '3203-150', '13398000.00'::numeric, '14737800.00'::numeric, NULL, FALSE),
  (1944, '3203-1506', '44038500.00'::numeric, '48442350.00'::numeric, '47100000.00'::numeric, TRUE),
  (1945, '3203-175', '16533000.00'::numeric, '18186300.00'::numeric, NULL, FALSE),
  (1946, '3203-200', '19173000.00'::numeric, '21090300.00'::numeric, NULL, FALSE),
  (1947, '3203-225', '20625000.00'::numeric, '22687500.00'::numeric, NULL, FALSE),
  (1948, '3203-250', '22704000.00'::numeric, '24974400.00'::numeric, NULL, FALSE),
  (1949, '3203-275', '25674000.00'::numeric, '28241400.00'::numeric, NULL, FALSE),
  (1950, '3203-300', '27423000.00'::numeric, '30165300.00'::numeric, NULL, FALSE),
  (1952, '3203-3012', '248820000.00'::numeric, '273702000.00'::numeric, NULL, FALSE),
  (1958, '3205-400', '91410000.00'::numeric, '100551000.00'::numeric, NULL, FALSE),
  (1971, '3222-500', '50490000.00'::numeric, '55539000.00'::numeric, NULL, FALSE),
  (2014, '4605-201', '3300000.00'::numeric, '3630000.00'::numeric, NULL, FALSE),
  (2016, '4621-100', '5841000.00'::numeric, '6425100.00'::numeric, NULL, FALSE),
  (2026, '4799-1150', '8943000.00'::numeric, '9837300.00'::numeric, NULL, FALSE),
  (2027, '4799-1200', '14388000.00'::numeric, '15826800.00'::numeric, NULL, FALSE),
  (2028, '4799-1300', '17193000.00'::numeric, '18912300.00'::numeric, NULL, FALSE),
  (2029, '4799-180', '6171000.00'::numeric, '6788100.00'::numeric, NULL, FALSE),
  (2034, '4820-552', '3729000.00'::numeric, '4101900.00'::numeric, NULL, FALSE),
  (2040, '4903-150', '30822000.00'::numeric, '33904200.00'::numeric, NULL, FALSE),
  (2041, '4903-200', '33660000.00'::numeric, '37026000.00'::numeric, NULL, FALSE),
  (2042, '4903-300', '43890000.00'::numeric, '48279000.00'::numeric, NULL, FALSE),
  (2046, '4912-100', '2425500.00'::numeric, '2668050.00'::numeric, NULL, FALSE),
  (2047, '4913-250', '4224000.00'::numeric, '4646400.00'::numeric, NULL, FALSE),
  (2050, '4921-230', '4917000.00'::numeric, '5408700.00'::numeric, NULL, FALSE),
  (2051, '4922-100', '3267000.00'::numeric, '3593700.00'::numeric, NULL, FALSE),
  (2052, '4922-150', '4059000.00'::numeric, '4464900.00'::numeric, NULL, FALSE),
  (2053, '6202-100', '14949000.00'::numeric, '16443900.00'::numeric, NULL, FALSE),
  (2054, '6210-100', '27522000.00'::numeric, '30274200.00'::numeric, NULL, FALSE),
  (2055, '6282-2001', '910800.00'::numeric, '1001880.00'::numeric, NULL, FALSE),
  (2056, '6282-2002', '1006500.00'::numeric, '1107150.00'::numeric, NULL, FALSE),
  (2057, '6282-2003', '1042800.00'::numeric, '1147080.00'::numeric, NULL, FALSE),
  (2058, '6282-2004', '1062600.00'::numeric, '1168860.00'::numeric, NULL, FALSE),
  (2059, '6282-2005', '1122000.00'::numeric, '1234200.00'::numeric, NULL, FALSE),
  (2060, '6282-2007', '1125300.00'::numeric, '1237830.00'::numeric, NULL, FALSE),
  (2061, '6282-2009', '1247400.00'::numeric, '1372140.00'::numeric, NULL, FALSE),
  (2062, '6282-2013', '1471800.00'::numeric, '1618980.00'::numeric, NULL, FALSE),
  (2063, '6282-2017', '1927200.00'::numeric, '2119920.00'::numeric, NULL, FALSE),
  (2079, '7110-300', '3531000.00'::numeric, '3884100.00'::numeric, NULL, FALSE),
  (2083, '7111-500', '28545000.00'::numeric, '31399500.00'::numeric, NULL, FALSE),
  (2086, '7139-100', '1798500.00'::numeric, '1978350.00'::numeric, NULL, FALSE),
  (2089, '7247-150', '2376000.00'::numeric, '2613600.00'::numeric, NULL, FALSE),
  (2090, '7247-200', '2874300.00'::numeric, '3161730.00'::numeric, NULL, FALSE),
  (2091, '7247-300', '4224000.00'::numeric, '4646400.00'::numeric, NULL, FALSE),
  (2092, '7261-150', '3729000.00'::numeric, '4101900.00'::numeric, NULL, FALSE),
  (2093, '7261-200', '3795000.00'::numeric, '4174500.00'::numeric, NULL, FALSE),
  (2094, '7261-300', '5511000.00'::numeric, '6062100.00'::numeric, NULL, FALSE),
  (2095, '7262-150', '3696000.00'::numeric, '4065600.00'::numeric, NULL, FALSE),
  (2096, '7262-200', '4191000.00'::numeric, '4610100.00'::numeric, NULL, FALSE),
  (2097, '7262-300', '6600000.00'::numeric, '7260000.00'::numeric, NULL, FALSE),
  (2099, '7522-610', '3663000.00'::numeric, '4029300.00'::numeric, NULL, FALSE),
  (2101, '8602-200', '3432000.00'::numeric, '3775200.00'::numeric, NULL, FALSE),
  (2102, '9225-405', '17886000.00'::numeric, '19674600.00'::numeric, NULL, FALSE),
  (2103, '9247-190', '11715000.00'::numeric, '12886500.00'::numeric, NULL, FALSE),
  (2106, '9722-250', '633600.00'::numeric, '696960.00'::numeric, NULL, FALSE),
  (2107, '9723-400', '4884000.00'::numeric, '5372400.00'::numeric, NULL, FALSE),
  (3471, '1111-75', '9438000.00'::numeric, '10381800.00'::numeric, NULL, FALSE),
  (3483, '2308-10', '6996000.00'::numeric, '7695600.00'::numeric, NULL, FALSE),
  (3494, '2364-10', '14058000.00'::numeric, '15463800.00'::numeric, NULL, FALSE),
  (3515, '3220-30', '17688000.00'::numeric, '19456800.00'::numeric, NULL, FALSE),
  (3522, '3220-50', '19470000.00'::numeric, '21417000.00'::numeric, NULL, FALSE),
  (3524, '3220-75', '26829000.00'::numeric, '29511900.00'::numeric, NULL, FALSE),
  (3537, '6200-60', '4785000.00'::numeric, '5263500.00'::numeric, NULL, FALSE),
  (3538, '6201-60', '4917000.00'::numeric, '5408700.00'::numeric, NULL, FALSE),
  (3539, '6202-80', '7887000.00'::numeric, '8675700.00'::numeric, NULL, FALSE),
  (3540, '6207-80', '8778000.00'::numeric, '9655800.00'::numeric, NULL, FALSE),
  (3541, '6208-80', '11418000.00'::numeric, '12559800.00'::numeric, NULL, FALSE),
  (3543, '6301', '4455000.00'::numeric, '4900500.00'::numeric, NULL, FALSE),
  (3544, '4602-17', '1362900.00'::numeric, '1499190.00'::numeric, NULL, FALSE),
  (3545, '4602-32', '1914000.00'::numeric, '2105400.00'::numeric, NULL, FALSE),
  (3546, '4621-02', '4884000.00'::numeric, '5372400.00'::numeric, NULL, FALSE),
  (3547, '4206-1', '7887000.00'::numeric, '8675700.00'::numeric, NULL, FALSE),
  (3548, '3108-25', '24222000.00'::numeric, '26644200.00'::numeric, NULL, FALSE),
  (3549, '3108-50', '27324000.00'::numeric, '30056400.00'::numeric, NULL, FALSE),
  (3550, '3109-25', '15543000.00'::numeric, '17097300.00'::numeric, NULL, FALSE),
  (3551, '3109-50', '19701000.00'::numeric, '21671100.00'::numeric, NULL, FALSE),
  (3552, '4621-03', '3663000.00'::numeric, '4029300.00'::numeric, NULL, FALSE),
  (3553, '4621-04', '3663000.00'::numeric, '4029300.00'::numeric, NULL, FALSE),
  (3554, '4621-05', '2696100.00'::numeric, '2965710.00'::numeric, NULL, FALSE),
  (3555, '4621-06', '2422200.00'::numeric, '2664420.00'::numeric, NULL, FALSE),
  (3556, '3203-25', '6534000.00'::numeric, '7187400.00'::numeric, NULL, FALSE),
  (3557, '4621-07', '2422200.00'::numeric, '2664420.00'::numeric, NULL, FALSE),
  (3558, '4621-08', '2422200.00'::numeric, '2664420.00'::numeric, NULL, FALSE),
  (3560, '3203-75', '8250000.00'::numeric, '9075000.00'::numeric, NULL, FALSE),
  (3561, '4621-09', '2422200.00'::numeric, '2664420.00'::numeric, NULL, FALSE),
  (3562, '4621-10', '2696100.00'::numeric, '2965710.00'::numeric, NULL, FALSE),
  (3563, '4621-15', '2696100.00'::numeric, '2965710.00'::numeric, NULL, FALSE),
  (3564, '4621-20', '2689500.00'::numeric, '2958450.00'::numeric, NULL, FALSE),
  (3565, '4621-25', '2640000.00'::numeric, '2904000.00'::numeric, NULL, FALSE),
  (3566, '4621-30', '4785000.00'::numeric, '5263500.00'::numeric, NULL, FALSE),
  (3567, '4621-40', '5115000.00'::numeric, '5626500.00'::numeric, NULL, FALSE),
  (3568, '4621-50', '5115000.00'::numeric, '5626500.00'::numeric, NULL, FALSE),
  (3569, '4621-70', '5577000.00'::numeric, '6134700.00'::numeric, NULL, FALSE),
  (3571, '4621-90', '5841000.00'::numeric, '6425100.00'::numeric, NULL, FALSE),
  (3573, '3210-25', '9174000.00'::numeric, '10091400.00'::numeric, NULL, FALSE),
  (3575, '3400-25', '18579000.00'::numeric, '20436900.00'::numeric, NULL, FALSE),
  (3578, '1240-1501', '8679000.00'::numeric, '9546900.00'::numeric, NULL, FALSE),
  (3580, '1240-2001', '8580000.00'::numeric, '9438000.00'::numeric, NULL, FALSE),
  (3581, '1240-3001', '11682000.00'::numeric, '12850200.00'::numeric, NULL, FALSE),
  (3602, '6284-3', '1772100.00'::numeric, '1949310.00'::numeric, NULL, FALSE),
  (3604, '4790-0100', '11847000.00'::numeric, '13031700.00'::numeric, NULL, FALSE),
  (3607, '7114-3460', '7722000.00'::numeric, '8494200.00'::numeric, NULL, FALSE),
  (3611, '2112-10', '13563000.00'::numeric, '14919300.00'::numeric, NULL, FALSE),
  (3612, '2112-25', '22935000.00'::numeric, '25228500.00'::numeric, NULL, FALSE),
  (3614, '2380-08', '11220000.00'::numeric, '12342000.00'::numeric, NULL, FALSE),
  (3615, '2381-08', '11517000.00'::numeric, '12668700.00'::numeric, NULL, FALSE),
  (3616, '2381-02', '23364000.00'::numeric, '25700400.00'::numeric, NULL, FALSE),
  (3617, '2302-25', '10494000.00'::numeric, '11543400.00'::numeric, NULL, FALSE),
  (3618, '2310-30', '17490000.00'::numeric, '19239000.00'::numeric, NULL, FALSE),
  (3619, '2309-50', '31152000.00'::numeric, '34267200.00'::numeric, NULL, FALSE),
  (3620, '2313-1', '17391000.00'::numeric, '19130100.00'::numeric, NULL, FALSE),
  (3621, '2311-5', '9966000.00'::numeric, '10962600.00'::numeric, NULL, FALSE),
  (3622, '2301-10', '6006000.00'::numeric, '6606600.00'::numeric, NULL, FALSE),
  (3629, '2322-35', '23232000.00'::numeric, '25555200.00'::numeric, NULL, FALSE),
  (3630, '2322-60', '24453000.00'::numeric, '26898300.00'::numeric, NULL, FALSE),
  (3631, '2852-18', '29304000.00'::numeric, '32234400.00'::numeric, NULL, FALSE),
  (3632, '4602-20', '1455300.00'::numeric, '1600830.00'::numeric, NULL, FALSE),
  (3633, '1203-1003', '7986000.00'::numeric, '8784600.00'::numeric, NULL, FALSE),
  (3637, '2871-10', '18975000.00'::numeric, '20872500.00'::numeric, NULL, FALSE),
  (3639, 'S3-2824', '49929000.00'::numeric, '54921900.00'::numeric, '53400000.00'::numeric, TRUE),
  (3658, '4621-12', '2851200.00'::numeric, '3136320.00'::numeric, NULL, FALSE),
  (3660, '4621-60', '5577000.00'::numeric, '6134700.00'::numeric, NULL, FALSE),
  (3662, '4780-85', '2065800.00'::numeric, '2272380.00'::numeric, NULL, FALSE),
  (3666, '4801-17', '3399000.00'::numeric, '3738900.00'::numeric, NULL, FALSE),
  (3669, '4801-15', '3564000.00'::numeric, '3920400.00'::numeric, NULL, FALSE),
  (3672, '4835-1', '5940000.00'::numeric, '6534000.00'::numeric, NULL, FALSE),
  (3674, '4839-1', '11088000.00'::numeric, '12196800.00'::numeric, NULL, FALSE),
  (3676, '4833-1', '1600500.00'::numeric, '1760550.00'::numeric, NULL, FALSE),
  (3678, '4838-1', '6468000.00'::numeric, '7114800.00'::numeric, NULL, FALSE),
  (3682, '4842-1', '2531100.00'::numeric, '2784210.00'::numeric, NULL, FALSE),
  (3685, '4824-16', '13398000.00'::numeric, '14737800.00'::numeric, NULL, FALSE),
  (3691, '7110-1000', '18744000.00'::numeric, '20618400.00'::numeric, NULL, FALSE),
  (3700, 'ISF-F500', '37290000.00'::numeric, '41019000.00'::numeric, NULL, FALSE),
  (3707, '7523-3D5', '5412000.00'::numeric, '5953200.00'::numeric, NULL, FALSE),
  (3721, '8003-3', '7458000.00'::numeric, '8203800.00'::numeric, NULL, FALSE),
  (3732, '6284-82', '1531200.00'::numeric, '1684320.00'::numeric, NULL, FALSE),
  (3763, '2383-08', '26235000.00'::numeric, '28858500.00'::numeric, NULL, FALSE),
  (3790, '4806-20', '10296000.00'::numeric, '11325600.00'::numeric, NULL, FALSE),
  (3791, '4824-12', '12969000.00'::numeric, '14265900.00'::numeric, NULL, FALSE),
  (3794, '5024', '16434000.00'::numeric, '18077400.00'::numeric, NULL, FALSE),
  (3795, '6210-80', '22308000.00'::numeric, '24538800.00'::numeric, NULL, FALSE),
  (3799, '6229-80', '30426000.00'::numeric, '33468600.00'::numeric, NULL, FALSE),
  (3801, '6282-1201', '5247000.00'::numeric, '5771700.00'::numeric, NULL, FALSE),
  (3804, '6282-1601', '2293500.00'::numeric, '2522850.00'::numeric, NULL, FALSE),
  (3824, '7600-6', '2491500.00'::numeric, '2740650.00'::numeric, NULL, FALSE),
  (3826, '9561-50B', '8580000.00'::numeric, '9438000.00'::numeric, NULL, FALSE),
  (3827, '9561-70B', '10989000.00'::numeric, '12087900.00'::numeric, NULL, FALSE),
  (3835, 'ISO-1000FN', '69300000.00'::numeric, '76230000.00'::numeric, NULL, FALSE),
  (3837, 'ISQ-RM30', '9966000.00'::numeric, '10962600.00'::numeric, NULL, FALSE),
  (3841, '4608-31', '1834800.00'::numeric, '2018280.00'::numeric, NULL, FALSE),
  (3845, '4120-10', '9900000.00'::numeric, '10890000.00'::numeric, NULL, FALSE),
  (3872, '4130-4', '6237000.00'::numeric, '6860700.00'::numeric, NULL, FALSE),
  (3873, '4130-5', '6237000.00'::numeric, '6860700.00'::numeric, NULL, FALSE),
  (3878, '4130-10', '6897000.00'::numeric, '7586700.00'::numeric, NULL, FALSE),
  (3895, '0312-TH50', '9669000.00'::numeric, '10635900.00'::numeric, NULL, FALSE),
  (3899, '1110-150A', '41910000.00'::numeric, '46101000.00'::numeric, NULL, FALSE),
  (3900, '1110-300A', '69960000.00'::numeric, '76956000.00'::numeric, NULL, FALSE),
  (3905, '1205-200S', '10824000.00'::numeric, '11906400.00'::numeric, NULL, FALSE),
  (4026, '4621-35', '4950000.00'::numeric, '5445000.00'::numeric, NULL, FALSE),
  (4033, '4829-1', '2174700.00'::numeric, '2392170.00'::numeric, NULL, FALSE),
  (4034, '4830', '7623000.00'::numeric, '8385300.00'::numeric, NULL, FALSE),
  (4048, '4845-2', '6765000.00'::numeric, '7441500.00'::numeric, NULL, FALSE),
  (4056, '4917-30', '32472000.00'::numeric, '35719200.00'::numeric, NULL, FALSE),
  (4058, '5013', '58410000.00'::numeric, '64251000.00'::numeric, NULL, FALSE),
  (4065, '6228-40', '29535000.00'::numeric, '32488500.00'::numeric, NULL, FALSE),
  (4066, '6298-2', '1574100.00'::numeric, '1731510.00'::numeric, NULL, FALSE),
  (4113, '9241-ML200', '11517000.00'::numeric, '12668700.00'::numeric, NULL, FALSE),
  (4116, '9563-C40', '26235000.00'::numeric, '28858500.00'::numeric, NULL, FALSE),
  (4117, 'DSW-A010', '11517000.00'::numeric, '12668700.00'::numeric, NULL, FALSE),
  (4140, '5042', '27588000.00'::numeric, '30346800.00'::numeric, NULL, FALSE);

DO $$
DECLARE
  expected_n integer := 206;
  expected_exception_n integer := 2;
  guard_n integer;
  updated_n integer;
  log_n integer;
  orig_n integer;
  orig_log_n integer;
BEGIN
  SELECT COUNT(*) INTO orig_n
  FROM insize_p110_rollback_expected
  WHERE clear_original_exception IS TRUE AND product_id NOT IN ();
  IF orig_n > 0 THEN
    RAISE EXCEPTION 'rollback exception flags outside whitelist=%', orig_n;
  END IF;

  SELECT COUNT(*) INTO guard_n
  FROM insize_p110_rollback_expected e
  JOIN products p ON p.id = e.product_id
  WHERE p.deleted_at IS NULL
    AND p.brand_id = 3
    AND p.sku IS NOT DISTINCT FROM e.expected_sku
    AND p.base_price IS NOT DISTINCT FROM e.applied_base_price;
  IF guard_n <> expected_n THEN
    RAISE EXCEPTION 'rollback guard failed: matching applied base rows=% expected=%', guard_n, expected_n;
  END IF;

  UPDATE products p
  SET base_price = e.restore_base_price,
      updated_at = NOW()
  FROM insize_p110_rollback_expected e
  WHERE p.id = e.product_id
    AND p.deleted_at IS NULL
    AND p.brand_id = 3
    AND p.sku IS NOT DISTINCT FROM e.expected_sku
    AND p.base_price IS NOT DISTINCT FROM e.applied_base_price;
  GET DIAGNOSTICS updated_n = ROW_COUNT;
  IF updated_n <> expected_n THEN
    RAISE EXCEPTION 'rollback updated base rows=% expected=%', updated_n, expected_n;
  END IF;

  UPDATE products p
  SET original_price = e.restore_original_price,
      updated_at = NOW()
  FROM insize_p110_rollback_expected e
  WHERE p.id = e.product_id
    AND e.clear_original_exception IS TRUE
    AND p.deleted_at IS NULL
    AND p.brand_id = 3
    AND p.original_price IS NULL;
  GET DIAGNOSTICS orig_n = ROW_COUNT;
  IF orig_n <> expected_exception_n THEN
    RAISE EXCEPTION 'rollback original restore rows=% expected=%', orig_n, expected_exception_n;
  END IF;

  INSERT INTO product_change_logs (product_id, field_name, old_value, new_value, reason, actor_user_id)
  SELECT e.product_id, 'base_price', e.applied_base_price::text, e.restore_base_price::text,
         'INSIZE +10% rollback restore exact pre-apply base_price 2026-10-21', NULL
  FROM insize_p110_rollback_expected e
  ORDER BY e.product_id;
  GET DIAGNOSTICS log_n = ROW_COUNT;
  IF log_n <> expected_n THEN
    RAISE EXCEPTION 'rollback base change_log rows=% expected=%', log_n, expected_n;
  END IF;

  INSERT INTO product_change_logs (product_id, field_name, old_value, new_value, reason, actor_user_id)
  SELECT e.product_id, 'original_price', NULL, e.restore_original_price::text,
         'INSIZE +10% rollback restore original_price (exceptions) 2026-10-21', NULL
  FROM insize_p110_rollback_expected e
  WHERE e.clear_original_exception IS TRUE
  ORDER BY e.product_id;
  GET DIAGNOSTICS orig_log_n = ROW_COUNT;
  IF orig_log_n <> expected_exception_n THEN
    RAISE EXCEPTION 'rollback original change_log rows=% expected=%', orig_log_n, expected_exception_n;
  END IF;
END $$;

COMMIT;
