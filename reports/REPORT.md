# Lab 25B — Report

**Họ tên / nhóm:** Đinh Mạnh Dũng — **MSV:** 2A202602975  
**Commit:** `b238648`
**Điểm tự động:** **84 / 88** với seed **25, 26, 27**; 4 điểm SLO hidden chưa có dữ liệu để chấm. Report/postmortem: giảng viên chấm riêng /12.

Môi trường kiểm chứng: Windows, Python 3.11. Các bảng chi tiết và thí nghiệm dùng seed 25; scoreboard dùng cả ba seed. File nguồn: [Game Day naive](gameday/naive.json), [Game Day resilient](gameday/resilient.json), [workflows](workflows.json), [SLO](slo.json), [cache](cache/cached.json), [thí nghiệm](experiments.json), [scoreboard](scoreboard.json). Thời gian và chi phí là đơn vị mô phỏng; chi phí không phải USD. Dữ liệu/băng ẩn của giảng viên chưa được kiểm chứng.

## 1. Kết quả Game Day (naive vs resilient)

| Băng | Client | availability | p95 (s) | amplification | retry_ratio | cost/turn | recovery (s) | PASS? |
|---|---|---:|---:|---:|---:|---:|---:|:---:|
| G1 | naive | 71.94% | 7.157 | 7.738 | 6.738 | 2.163 | 4 | FAIL |
| G1 | resilient | 100.00% | 4.817 | 1.06 | 0.001 | 2.094 | 0 | PASS |
| G2 | naive | 45.60% | 15.034 | 9.904 | 8.904 | 4.627 | 155 | FAIL |
| G2 | resilient | 100.00% | 10.781 | 1.038 | 0.005 | 2.116 | 0 | PASS |
| G3 | naive | 100.00% | 4.768 | 1.164 | 0.164 | 2.328 | 0 | FAIL |
| G3 | resilient | 100.00% | 4.718 | 1.065 | 0.035 | 2.146 | 0 | PASS |
| G4 | naive | 100.00% | 13.764 | 1.004 | 0.004 | 2.008 | 0 | FAIL |
| G4 | resilient | 100.00% | 5.684 | 1.013 | 0.002 | 2.069 | 0 | PASS |
| G5 | naive | 36.99% | 5.359 | 17.03 | 16.03 | 2.124 | — | FAIL |
| G5 | resilient | 81.79% | 5.482 | 1.003 | 0.002 | 2.504 | — | PASS |
| G6 | naive | 51.70% | 4.836 | 12.344 | 11.344 | 2.009 | 0 | FAIL |
| G6 | resilient | 100.00% | 6.225 | 1.067 | 0.027 | 2.164 | 0 | PASS |

Resilient PASS 6/6 băng trên từng seed 25, 26, 27. Trên seed 25, G1 có 0 vi phạm retry-after; G5 có 0 retry lỗi client và 0 failover không cần thiết; G6 có 0 route không tương thích. Traffic quay lại primary sau restore: G2 = 100.00%, G4 = 100.00%, G6 = 100.00%. G5 không có mốc restore nên recovery là “—”.

Recovery 0 giây nghĩa là cửa sổ **[restore, restore+30)** đã đạt ≥95% logical call thành công; không có nghĩa mọi provider đã đóng breaker ngay thời điểm restore. P95 chỉ tính trên lượt thành công, do đó phải đọc cùng availability.

## 2. Cấu hình client và lý do

Khối client giữ các giá trị starter sau khi xác nhận chúng đạt toàn bộ check trên ba seed. Cache được chỉnh riêng ở mục 8; không sửa mô tả thế giới, scenario hoặc grader.

| Tham số | Giá trị | Lý do dựa trên kết quả |
|---|---:|---|
| attempt_timeout_s | 8 | G6 đạt 100%; đổi sang 30 làm availability còn 94,88% và 103 GiveUp deadline. |
| max_attempts_per_provider | 2 | Một retry là đủ: G3 đạt 100% với retry_ratio 0,035; tránh nhiều attempt trong lúc provider nghẽn. |
| min_time_left_s | 1 | Không giữ permit cho attempt thiếu thời gian; test deadline PASS và G6 cấu hình cuối không có GiveUp deadline. |
| backoff_base_s / cap_s | 0,25 / 4 | Full jitter phân tán retry; G2 amplification 1,038, G1 có 0 vi phạm retry-after. |
| retry_budget_ratio | 0,1 | G3 retry_ratio 0,035, thấp hơn ngưỡng 0,10; khi breaker bị vô hiệu hóa, budget vẫn giảm G2 retry_ratio 0,400 → 0,058. |
| retry_budget_min_per_s / max_tokens | 0,5 / 20 | Cho phép retry lúc ít traffic và burst nhỏ ban đầu; G3 vẫn PASS. Đây là token bucket có token ban đầu và hồi theo thời gian, không phải trần 10% tuyệt đối trong mọi cửa sổ ngắn. |
| quota_cooldown_s | 300 | G5 tránh gửi liên tục vào account hết quota; availability 81,79%, 0 retry lỗi client và 0 failover không cần thiết. |
| breaker.window_size / min_calls | 20 / 10 | Chỉ giữ kết quả gần nhất, không trip từ một lỗi đơn lẻ; G2 amplification giảm từ naive 9,904 xuống 1,038. |
| failure_rate_threshold | 0,5 | Đủ nhạy với provider hỏng; G6 đạt 100% trong khi naive chỉ 51,70%. |
| slow_call_s / slow_rate_threshold | 5 / 0,6 | G4 có thành công chậm vẫn mở breaker; p95 giảm từ 13,764 xuống 5,684 giây. |
| open_duration_s | 10 | Provider được nghỉ và được kiểm tra lại; G2 recovery 0 giây, primary share sau restore 100%. |
| half_open_max_probes / half_open_successes | 2 / 2 | Giới hạn request thăm dò đồng thời, tránh dồn tải khi hồi phục; toàn bộ 13 test breaker PASS và G2/G6 quay lại primary. |

Sơ đồ quyết định của on_error:

| Loại lỗi | Ghi breaker? | Retry cùng provider? | Failover / cooldown |
|---|---|---|---|
| CLIENT_ERROR | release permit, không ghi sức khỏe | Không | GiveUp client_error ngay |
| QUOTA_EXHAUSTED | release | Không | Cooldown 300 giây, failover ngay |
| RATE_LIMITED | release | Không tại nhánh này | Cooldown ít nhất retry-after, failover ngay |
| OVERLOADED / SERVER_ERROR / TIMEOUT | on_failure | Chỉ khi còn lượt, budget, deadline và breaker cho phép | Hết điều kiện thì failover |

Nếu ladder đã hết, chỉ chờ cooldown **rate limit** ngắn ≤5 giây khi deadline còn đủ; thêm jitter phía sau thời điểm được phép. Không chờ quota hoặc breaker OPEN. Cooldown dùng chung cho các call; mỗi call mới bắt đầu từ primary. Tool call lọc theo supports_tools. Thành công báo cả latency; cancel trả lại permit.

## 3. Ba thí nghiệm client

Các thí nghiệm nằm trong script [run_experiments.py](../scripts/run_experiments.py). Chúng tạo cấu hình/client đối chứng trong bộ nhớ; không thay cấu hình nộp bài. Tất cả dùng cùng seed 25.

### 3.1. Retry budget là lớp phòng thủ cuối

Đặt max_attempts_per_provider = 5. Với breaker_off, đặt min_calls = 1000000000. Với budget_off, đặt ratio = 100, max_tokens = 1e9, min_per_s = 1e6.

| Cấu hình | Băng | availability | amplification | retry_ratio | recovery (s) |
|---|---|---:|---:|---:|---:|
| breaker_off_budget_on | G2 | 99.83% | 1.378 | 0.058 | 0 |
| breaker_off_budget_on | G3 | 100.00% | 1.136 | 0.068 | 0 |
| breaker_off_budget_off | G2 | 96.70% | 1.597 | 0.4 | 32 |
| breaker_off_budget_off | G3 | 100.00% | 1.162 | 0.158 | 0 |
| breaker_on_budget_on | G2 | 100.00% | 1.049 | 0.006 | 0 |
| breaker_on_budget_on | G3 | 100.00% | 1.036 | 0.02 | 0 |
| breaker_on_budget_off | G2 | 100.00% | 1.049 | 0.006 | 0 |
| breaker_on_budget_off | G3 | 100.00% | 1.036 | 0.02 | 0 |

Khi breaker không hoạt động, budget giảm G2 amplification 1,597 → 1,378, retry_ratio 0,400 → 0,058, recovery 32 → 0 giây. Trên G3, retry_ratio giảm 0,158 → 0,068 trong khi availability vẫn 100%. Khi breaker hoạt động, bật/tắt budget cho cùng kết quả trên seed này: breaker đã chặn phần lớn attempt trước khi budget trở thành yếu tố giới hạn. Vẫn cần cả hai vì breaker bảo vệ từng provider dựa trên quan sát sức khỏe, còn budget chặn lượng retry toàn cục kể cả khi breaker bị cấu hình sai hoặc chưa đủ mẫu.

### 3.2. attempt_timeout_s = 30

| Timeout (s) | Băng | availability | p95 (s) | give_up_reasons |
|---|---|---:|---:|---|
| 30 | G6 | 94.88% | 5.445 | {"deadline":103,"no_provider_available":19} |
| 30 | G4 | 100.00% | 5.608 | {} |
| 8.0 | G6 | 100.00% | 6.225 | {} |
| 8.0 | G4 | 100.00% | 5.684 | {} |

G6 timeout 30 giây giảm availability từ 100% xuống 94,88%, với 103 deadline và 19 no_provider_available; provider alpha-eu treo làm mất phần thời gian cần để chuyển sang beta. P95 lại giảm 6,225 → 5,445 giây vì những lượt treo rồi thất bại không có trong tập tính p95: đây là survivorship bias. G4 gần như không đổi vì alpha chỉ thêm 5 giây, thường trả trước timeout 8 giây, và slow-call breaker vẫn nhận ra suy giảm. Chọn timeout từ latency tail của attempt lúc bình thường, nhưng phải chừa thời gian cho fallback và cả lượt tool + chat trong deadline 30 giây; không lấy p99 toàn lượt làm timeout cho từng attempt.

### 3.3. Bỏ lọc tool calling

| Ladder | availability G6 | incompatible_routes | cost/turn |
|---|---:|---:|---:|
| Lọc capability | 100,00% | 0 | 2,164 |
| Không lọc | 90,15% | 235 | 2,284 |

Có 235 lượt bị kết thúc vì incompatible_model_output. Với người dùng, đây là model trả được văn bản nhưng không thực hiện được thao tác hoàn tiền mà sản phẩm cần; một phản hồi kỹ thuật thành công chưa đủ để lượt user thành công. Vì vậy model rẻ gamma-mini chỉ được dùng cho chat, không được dùng cho bước chọn tool. Chi phí mỗi lượt tốt còn tăng khi không lọc vì hệ thống đã trả tiền cho các lượt không hoàn thành.

## 4. Workflow hoàn tiền

| Executor | completion | crashes | duplicate refunds | duplicate emails | lost refunds | overpaid (cents) | wasted LLM / crash |
|---|---:|---:|---:|---:|---:|---:|---:|
| naive | 100.00% | 81 | 128 | 81 | 0 | 1496700 | 1.123 |
| yours | 100.00% | 66 | 0 | 0 | 0 | 0 | 0.303 |

Executor mới chạy 500 session với 500 payment execution và 2.500 checkpoint; không mất hoàn tiền, không trả thừa, hoàn tất 100%. Wasted LLM giảm từ 91 xuống 20 call, tương ứng 1,123 → 0,303 call/crash. Các số crash khác nhau giữa hai executor do số lần gọi service làm thay đổi chuỗi random fault, nên không so chúng như số crash cố định được tiêm giống nhau.

Idempotency key ổn định theo session + step ngăn payment/email chạy lại khi response bị mất hoặc worker chết sau side effect. Chỉ idempotency chưa đủ: các bước đọc/LLM vẫn bị chạy lại và tốn tiền nếu không có checkpoint. Chỉ checkpoint chưa đủ: crash có thể xảy ra sau khi payment đã chuyển tiền nhưng trước khi lưu checkpoint, khi đó worker mới sẽ gọi payment lần nữa. Ghi checkpoint trước payment có thể đánh dấu “đã làm” dù worker chết trước lúc chuyển tiền, gây mất hoàn tiền; thứ tự đúng là chạy step thành công rồi lưu kết quả. WorkerCrash được truyền ra cho runner khởi động worker mới.

## 5. Alerting & error budget

| Sự cố | Mong đợi | Naive alerter | Burn-rate alerter | Độ trễ burn-rate (phút) |
|---|---|---|---|---:|
| checkout_bug | page | page (1 phút) | page (27 phút) | 27 |
| provider_outage | page | page (0 phút) | page (4 phút) | 4 |
| deploy_blip | none | page sai | không page | — |
| slow_leak | ticket | không phát hiện | ticket (1337 phút) | 1337 |
| degraded_evening | page | page (214 phút) | page (291 phút) | 291 |
| night_spike | none | page sai | không page | — |
| small_bump | none | page sai | không page | — |

Burn-rate có 3 page episode, 1 ticket và **0 false page**, so với naive 7 page episode, 0 ticket và 3 false page. Luật dùng AND của cửa sổ dài/ngắn: page 14,4× (60/5 phút), page 6× (360/30 phút), ticket 1× (4.320/360 phút). Prefix sum cho tổng mỗi cửa sổ trong O(1); episode kết thúc ở phút đầu không còn firing và end_min là exclusive.

Error budget của 30 ngày dữ liệu:

- Requests: **25.901.755**; bad: **55.618**; availability: **99,7853%**.
- SLO 99,5% cho phép **129.508,8** bad request (làm tròn một chữ số).
- Đã tiêu **42,95%**, còn **57,05%** budget; **không freeze release** vì budget_remaining > 0.

small_bump kéo dài 20 phút ở 12% lỗi không nên page chỉ theo ngưỡng 5 phút: mức lỗi cao nhưng thời gian ngắn chưa tiêu đủ budget cho page nhiều cửa sổ. Ngay cả giả sử traffic đều và nền không lỗi, cửa sổ 1 giờ chỉ có 4% lỗi, burn 8× <14,4×; cửa sổ 6 giờ có khoảng 0,667%, burn 1,333× <6×. Với dữ liệu thực tế, burn-rate không page sự kiện này; naive có page sai. Quyết định page phụ thuộc tác động và tốc độ tiêu budget, không phụ thuộc giờ trưa hay chỉ tỷ lệ lỗi tức thời.

## 6. Postmortem — G2 với client naive (blameless)

![Game Day G2: retry amplification và call success](gameday/G2_overload_storm.png)

### Tóm tắt

Tại t=120, alpha mất 75% năng lực trong 180 giây. Retry nhiều tầng không có jitter, budget, breaker hoặc fallback khuếch đại tải lên 9,904 attempt/logical call, làm các lượt user thất bại tiếp dù GPU đã phục hồi ở t=300. Hệ thống chỉ đạt ngưỡng hồi phục ở t=455; client mới giữ 100% availability và amplification 1,038 trên cùng seed.

### Ảnh hưởng

Có **1285/2362 lượt user thất bại** (54.40%) trong băng 600 giây. Từ trigger đến cửa sổ hồi phục là **335 giây**; có **155 giây** ảnh hưởng kéo dài sau restore. P95 của các lượt thành công là 15,034 giây, không phản ánh đầy đủ các lượt chờ rồi thất bại. Naive có 34.475 attempt, 2.737 client timeout và 26.298 lỗi rate limit; resilient có 4905 attempt và không mất lượt user nào.

Nếu tháng chỉ có sự cố này và workload đều 4 lượt user/giây, tháng 30 ngày có 10.368.000 lượt; SLO 99,5% cho phép 51.840 lượt thất bại. 1285 lượt thất bại tiêu **2.48% error budget tháng**, tương đương 321.25 giây mất toàn bộ traffic. Không vượt tổng budget tháng theo giả định này; lỗi vượt tỷ lệ cho phép trong chính băng sự cố là vấn đề khác. Phép tính này dùng đơn vị lượt user, tách khỏi dữ liệu request 30 ngày ở mục 5.

### Timeline

Nguồn: [CSV naive G2](gameday/naive_G2_overload_storm_timeseries.csv). attempts/s là trung bình trên khoảng giây ghi trong bảng; success ratio = tổng calls_ok / tổng calls_done, không lấy trung bình các tỷ lệ theo giây. Đây là logical-call success, khác availability theo lượt user.

| t (giây ảo, inclusive) | Sự kiện | alpha attempts/s | call success ratio |
|---|---|---:|---:|
| 110–119 | Trước sự cố | 9.10 | 92/92 = 100.00% |
| 120–129 | GPU alpha còn 25%; kết quả cũ vẫn đang về | 6.20 | 32/32 = 100.00% |
| 140–149 | Retry storm hình thành | 214.20 | 0/47 = 0.00% |
| 180–189 | Lỗi và retry duy trì tải | 148.10 | 0/43 = 0.00% |
| 300–309 | GPU đã phục hồi nhưng user vẫn thất bại | 38.80 | 0/18 = 0.00% |
| 350–359 | Chưa thoát trạng thái nghẽn | 17.90 | 0/39 = 0.00% |
| 420–429 | Tải lại tăng, success vẫn bằng 0 | 39.10 | 0/33 = 0.00% |
| 455–484 | Cửa sổ 30 giây đầu tiên đạt ngưỡng hồi phục | 10.87 | 352/368 = 95.65% |
| 480–489 | Trở lại bình thường | 10.60 | 124/124 = 100.00% |

Cửa sổ [455,485) đạt 352/368 = 95,65%, khớp recovery_s = 155. Cửa sổ [300,310) vẫn 0/18 dù năng lực GPU đã hồi phục. Không kết luận failure từ giây có calls_done = 0; dùng các cửa sổ có mẫu số dương như trên.

### Trigger và root cause

Trigger là alpha mất GPU. Root cause phía ứng dụng là thiết kế app × gateway × SDK retry tới 36 attempt/call, delay cố định, không kiểm soát tổng retry, không breaker và không tuyến fallback. Timeout của client không hủy công việc tại provider: hàng đợi chứa cả request mà user/client đã bỏ. Lỗi do hàng đợi và rate limit kích hoạt thêm retry, retry lại tạo thêm tải, khiến request mới tiếp tục timeout hoặc bị từ chối. Vòng phản hồi này duy trì trạng thái metastable sau t=300; công suất phục hồi không đồng nghĩa hàng đợi và feedback loop đã hết.

### Điều giúp và điều làm tệ hơn

Cooldown dùng chung tránh retry sớm vào tenant bị giới hạn; breaker tạm dừng provider lỗi/chậm; fallback chuyển công việc sang capacity khác. Kết quả G2 resilient: amplification 1,038, cost/turn 2,116 thay vì 4,627, recovery 0 giây. Retry cố định và ba tầng retry của v1 làm tệ hơn bằng cách tạo burst đồng bộ và bỏ qua retry-after (28.381 vi phạm trên G2). Khắc phục tập trung vào cấu hình mặc định, ranh giới retry và kiểm thử suy giảm; không quy lỗi cho cá nhân vận hành.

### Action items

| # | Hành động | Loại | Owner | Cách kiểm chứng |
|---|---|---|---|---|
| 1 | Chỉ để retry tại client; tắt retry lồng ở gateway/SDK khi tích hợp thực | prevent | Đinh Mạnh Dũng — client | CI G2 amplification ≤1,6 và G3 retry_ratio ≤0,10 trên ≥3 seed |
| 2 | Giữ retry budget, full jitter và cooldown dùng chung | prevent | Đinh Mạnh Dũng — reliability | Test budget/jitter PASS; G1 retry_after_violations = 0 |
| 3 | Cảnh báo theo nhiều cửa sổ và theo dõi attempt amplification/provider health | detect | On-call ShopAgent | SLO public có 0 false page; mọi page/ticket đúng hạn; dashboard hiển thị provider error/timeout |
| 4 | Bật breaker slow-call và fallback có capability; giới hạn HALF_OPEN probe | mitigate | Đinh Mạnh Dũng — routing | G2 recovery ≤30 giây, G4 p95 ≤10 giây, G6 incompatible_routes = 0, primary share ≥80% |
| 5 | Dùng idempotency + checkpoint cho payment/email | prevent | Đinh Mạnh Dũng — workflow | 500 workflow/seed: không trùng/mất side effect, completion ≥99%, wasted LLM/crash ≤0,6 |

## 7. Một điểm yếu còn lại

G2 resilient vẫn có p95 **10,781 giây**, cao hơn các băng khác: những call đang bay phải chờ timeout hoặc kết quả chậm trước khi breaker/fallback phát huy tác dụng. G6 cost/turn **2,164**, cao hơn naive **2,009**, nhưng naive mất 48,30% lượt user nên không thể coi chi phí thấp là kết quả tốt. Nếu mọi provider cùng chậm và không có cache phù hợp, fallback không tạo thêm năng lực. Hướng cải tiến: đo latency attempt theo provider, cân nhắc timeout thích ứng có giới hạn deadline, giới hạn in-flight/admission control và đánh giá lại p95, availability, amplification cùng chi phí trên băng biến thể trước khi đổi cấu hình.

## 8. Cache (Part G)

| Client | availability | faq_availability | cache_hit_ratio | stale_served | wrong_answers | outdated_answers | cost/turn | PASS? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| resilient | 83.73% | 84.24% | 0.00% | 0 | 0 | 0 | 1.386 | FAIL |
| cached | 91.24% | 96.45% | 65.20% | 157 | 0 | 3 | 0.915 | PASS |

Khối cache cuối: similarity_threshold = 0,90; ttl_s = 60; max_stale_s = 600; max_entries = 500. C1 PASS trên từng seed 25, 26, 27. Availability toàn hệ thống vẫn chỉ 91,24% vì tool workflow và câu hỏi cá nhân không thể được cache cứu khi toàn bộ provider sập; FAQ availability là 96,45%.

| Tham số | Giá trị | Lý do bằng số liệu |
|---|---:|---|
| similarity_threshold | 0,90 | Ngưỡng 0,80 gây 157 other_question; 0,90 có 0 wrong answer và hit 65,2%; 0,97 giảm hit xuống 58,1%. |
| ttl_s | 60 | TTL 300 gây 95 outdated, vượt giới hạn 15; TTL 60 chỉ 3 outdated, hit cao hơn TTL 30 (65,2% vs 59,2%). |
| max_stale_s | 600 | Phục vụ 157 stale; bỏ stale làm FAQ availability 96,45% → 87,33%, không còn đạt 93%. Thời gian stale dài chỉ được dùng khi provider bỏ cuộc. |
| max_entries | 500 | Giới hạn bộ nhớ bằng LRU, đủ cho bộ FAQ public; test eviction PASS. Đây là giới hạn capacity, không dùng để đánh đổi việc cache dữ liệu cá nhân. |

### Các đối chứng

Các hàng chỉ đổi tham số ghi trong tên, giữ các tham số còn lại theo cấu hình cuối; starter dùng 0,80 / TTL 600 / stale 0 như repo ban đầu.

| Cấu hình | FAQ availability | hit ratio | wrong | outdated | stale served | cost/turn |
|---|---:|---:|---:|---:|---:|---:|
| starter | 85.87% | 74.20% | 181 | 80 | 0 | 0.921 |
| final | 96.45% | 65.20% | 0 | 3 | 157 | 0.915 |
| threshold_0.80 | 87.33% | 66.60% | 157 | 1 | 152 | 0.965 |
| threshold_0.97 | 96.40% | 58.10% | 0 | 4 | 153 | 0.964 |
| ttl_30 | 96.45% | 59.20% | 0 | 2 | 192 | 0.955 |
| ttl_300 | 96.40% | 73.10% | 0 | 95 | 68 | 0.863 |
| no_stale | 87.33% | 56.10% | 0 | 3 | 0 | 0.975 |

**Ngưỡng:** 0,80 có wrong_answers_by_reason = {other_question: 157}. Đây là false hit giữa những câu hỏi gần nhau về embedding nhưng khác ý định; catalog có các cặp chính sách hoàn tiền/thời gian hoàn tiền, đổi size/đổi màu, phí ship nội thành/ngoại tỉnh và hình thức thanh toán/COD. Counter chỉ ghi nguyên nhân, không cho số theo từng cặp, nên không gán toàn bộ 157 lỗi cho một cặp cụ thể. Ngưỡng 0,90 loại false hit trong thực nghiệm; 0,97 cũng an toàn nhưng bỏ lỡ nhiều paraphrase, tăng cost/turn 0,915 → 0,964.

**TTL:** TTL 30/60/300 có outdated 2/3/95 và hit 59,2%/65,2%/73,1%. Webhook xử lý cập nhật có thông báo ở t=150, nhưng cập nhật phí ship t=480 không thông báo nên không có invalidate để gọi; TTL là giới hạn độ tươi khi provider khỏe. TTL 60 được chọn vì giữ outdated dưới 15 và hit trên 50%. Trong outage, stale-if-error chủ động cho phép vượt TTL; TTL không đảm bảo câu trả lời không bao giờ cũ.

**Stale-if-error:** max_stale_s = 0 làm stale served 157 → 0 và FAQ availability 96,45% → 87,33%; hit giảm 65,2% → 56,1%. Provider còn hoạt động thì entry quá TTL được refresh, không phục vụ stale ngay. Khi GiveUp, lookup lại để áp dụng invalidation/scope hiện tại trước khi Serve; stale không được vượt tuổi ttl_s + max_stale_s.

Câu hỏi cá nhân như “Đơn #48213 của tôi đang ở đâu?” không được cache kể cả theo user: trạng thái đơn/tiền hoàn/điểm có thể đổi liên tục, embedding không chứng minh trạng thái dữ liệu còn đúng, và trả lời cũ có thể khiến user hành động sai. Chặn personal ở cả store và lookup, tách prompt_version, và invalidate theo nguồn đều có unit test.

Dashboard user có thể còn xanh nhờ cache trong lúc provider sập. Cần theo dõi riêng error/timeout và tỷ lệ breaker OPEN của từng provider, số GiveUp bị cache che, stale_served/stale age và tỷ lệ refresh thất bại; kết hợp alert sức khỏe dependency với SLO user. Ví dụ seed 25 có 157 stale served trong C1: đây là bằng chứng dependency suy giảm dù FAQ availability vẫn 96,45%. Không cộng stale thành lỗi SLO user một cách máy móc, nhưng phải cho on-call biết đang dùng lớp dự phòng.

## Tái lập kết quả và nộp bài

Trên máy đã có .venv, chạy toàn bài bằng `scripts\verify.cmd` (không cần đổi execution policy của PowerShell). Script kiểm tra điểm public ≥84 sau khi chạy grader. Để cài từ đầu hoặc chạy từng bước, dùng PowerShell tại thư mục gốc:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,plot]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/run_gameday.py --client both
.\.venv\Scripts\python.exe scripts/run_workflows.py --executor both
.\.venv\Scripts\python.exe scripts/run_slo.py --alerter both
.\.venv\Scripts\python.exe scripts/run_gameday.py --scenarios configs/scenarios_cache.yaml --client resilient,cached --out reports/cache
.\.venv\Scripts\python.exe scripts/run_experiments.py
$env:MPLBACKEND = "Agg"
$env:MPLCONFIGDIR = "$PWD\.venv\matplotlib-cache"
.\.venv\Scripts\python.exe scripts/plot_timeseries.py --scenario G2_overload_storm
.\.venv\Scripts\python.exe scripts/grade.py --seeds 25,26,27
```

Kiểm chứng: 82/82 test PASS; ruff và mypy PASS trên 7 file triển khai. Không sửa simulator, tests có sẵn, scenario, naive client/executor hoặc services/runner/scoring/data được cung cấp. Không dùng thời gian thật hay tên/thời điểm băng trong client/cache.

Báo cáo ghi hash commit triển khai; JSON/CSV/ảnh được lưu trong Git cùng code. Repo theo quy tắc tên của lớp: Track3-Day25-2A202602975-Dinh-Manh-Dung. Khi nộp, kiểm tra repo ở chế độ public và nộp link repo lên kênh của lớp.
