export const article = {
  year: 2002,
  section: 'Text 1',
  title: 'Humor that works with an audience',
  zhTitle: '怎样让幽默真正对听众奏效',
  background: '一篇讲“演讲中的幽默”的实用说明文。整体应轻松、清晰、有交流感；中段天堂笑话要像讲故事一样逐渐铺垫，最后用克制的冷幽默落点。',
};

const d = (mood, label, rate = 1, pitch = 1, pause = 260, role = 'narrator', spoken = null) => ({ mood, label, rate, pitch, pause, role, spoken });

export const sentences = [
  {id:1,en:'If you intend using humor in your talk to make people smile, you must know how to identify shared experiences and problems.',zh:'如果你打算在讲话中运用幽默来博人一笑，就必须懂得找出你与听众共同的经历和问题。',vocab:[],director:d('warm','🙂 轻松讲解',.96,1.01,280)},
  {id:2,en:'Your humor must be relevant to the audience and should help to show them that you are one of them or that you understand their situation and are in sympathy with their point of view.',zh:'你的幽默必须贴合听众，并让他们感受到：你是他们中的一员，或者至少你理解他们的处境，也认同他们看待问题的立场。',vocab:[],director:d('warm','🙂 亲切说明',.94,1,300)},
  {id:3,en:'Depending on whom you are addressing, the problems will be different.',zh:'面对不同的听众，你所谈的问题自然也应有所不同。',vocab:[],director:d('clear','💡 提醒重点',.98,1.03,240)},
  {id:4,en:'If you are talking to a group of managers, you may refer to the disorganized methods of their secretaries; alternatively, if you are addressing secretaries, you may want to comment on their disorganized bosses.',zh:'如果你面对的是一群经理，可以拿他们秘书做事杂乱无章来开玩笑；反过来，如果面对的是秘书，你也可以调侃她们那些毫无条理的老板。',vocab:[{word:'disorganized',level:6,meaning:'杂乱无章的'},{word:'alternatively',level:6,meaning:'或者；换个角度说'}],director:d('playful','😏 轻微调侃',.96,1.05,360)},
  {id:5,en:"Here is an example, which I heard at a nurses' convention, of a story which works well because the audience all shared the same view of doctors.",zh:'下面这个例子是我在一次护士大会上听到的；这个故事之所以效果很好，正是因为在场听众对医生都有着相同的看法。',vocab:[{word:'convention',level:6,meaning:'大会；会议'}],director:d('story','🎬 开始讲故事',.9,1,430)},
  {id:6,en:'A man arrives in heaven and is being shown around by St. Peter.',zh:'一个人来到天堂，圣彼得正带着他四处参观。',vocab:[],director:d('story','☁️ 场景展开',.88,1.03,380)},
  {id:7,en:'He sees wonderful accommodations, beautiful gardens, sunny weather, and so on.',zh:'他看到舒适宜人的住所、美丽的花园、明媚的阳光，诸如此类。',vocab:[{word:'accommodations',level:6,meaning:'住宿设施；住处'}],director:d('bright','🌤️ 明亮画面',.9,1.08,390)},
  {id:8,en:'Everyone is very peaceful, polite and friendly until, waiting in a line for lunch, the new arrival is suddenly pushed aside by a man in a white coat, who rushes to the head of the line, grabs his food and stomps over to a table by himself.',zh:'那里人人都安详、礼貌而友善——直到排队吃午饭时，一个身穿白大褂的人突然把这位新来者挤到一旁，冲到队伍最前面，抓起食物，又大步走到一张桌子旁独自坐下。',vocab:[{word:'stomps',level:7,meaning:'重步走；跺着脚走'}],director:d('tension','⚡ 突然转折',.96,1.08,500,'narrator','Everyone is very peaceful, polite and friendly... until, waiting in a line for lunch, the new arrival is suddenly pushed aside by a man in a white coat, who rushes to the head of the line, grabs his food, and stomps over to a table by himself.')},
  {id:9,en:'“Who is that?” the new arrival asked St. Peter.',zh:'“那是谁？”新来的人问圣彼得。',vocab:[],director:d('curious','❓ 好奇追问',.82,1.18,520,'dialogue')},
  {id:10,en:'“Oh, that’s God,” came the reply, “but sometimes he thinks he’s a doctor.”',zh:'“哦，那是上帝，”圣彼得回答，“不过有时候，他会以为自己是个医生。”',vocab:[],director:d('punchline','😐 冷幽默落点',.78,.92,760,'dialogue',"Oh, that's God... but sometimes... he thinks he's a doctor.")},
  {id:11,en:"If you are part of the group which you are addressing, you will be in a position to know the experiences and problems which are common to all of you and it'll be appropriate for you to make a passing remark about the inedible canteen food or the chairman's notorious bad taste in ties.",zh:'如果你本身就是听众群体中的一员，自然就了解大家共同的经历和烦恼；这时，你随口调侃一下食堂里难以下咽的饭菜，或者主席那出了名的糟糕领带品味，都是合适的。',vocab:[{word:'inedible',level:7,meaning:'难以下咽的'},{word:'notorious',level:6,meaning:'臭名昭著的；出了名的'}],director:d('clear','📌 回到解释',.93,.99,310)},
  {id:12,en:"With other audiences you mustn't attempt to cut in with humor as they will resent an outsider making disparaging remarks about their canteen or their chairman.",zh:'但面对其他群体时，就不要贸然插入这种幽默，因为他们会反感一个外人贬损自己的食堂或主席。',vocab:[{word:'resent',level:6,meaning:'对……感到愤恨；反感'},{word:'disparaging',level:8,meaning:'贬损的；轻蔑的'}],director:d('warning','⚠️ 稍严肃提醒',.91,.94,340)},
  {id:13,en:'You will be on safer ground if you stick to scapegoats like the Post Office or the telephone system.',zh:'如果实在想开玩笑，最好拿邮政局或电话系统这类人人都可以抱怨的“替罪羊”下手，这样要安全得多。',vocab:[{word:'scapegoats',level:8,meaning:'替罪羊'}],director:d('playful','😉 轻松收束',.93,1.04,380)},
  {id:14,en:'If you feel awkward being humorous, you must practice so that it becomes more natural.',zh:'如果你觉得讲幽默时很不自在，那就必须多加练习，让它逐渐变得自然。',vocab:[{word:'awkward',level:6,meaning:'不自在的；笨拙的'}],director:d('encourage','🌱 鼓励',.93,1.04,300)},
  {id:15,en:'Include a few casual and apparently off-the-cuff remarks which you can deliver in a relaxed and unforced manner.',zh:'你可以穿插几句随意的、看似即兴而出的评论，并用轻松、不做作的方式把它们说出来。',vocab:[{word:'off-the-cuff',level:8,meaning:'即兴的；未经准备的'},{word:'unforced',level:6,meaning:'自然的；不勉强的'}],director:d('relaxed','🫧 放松自然',.89,.99,330)},
  {id:16,en:"Often it's the delivery which causes the audience to smile, so speak slowly and remember that a raised eyebrow or an unbelieving look may help to show that you are making a light-hearted remark.",zh:'很多时候，真正让听众发笑的其实是表达方式；所以说话要慢一些，也别忘了，一个挑眉或故作不信的神情，都能帮助听众意识到你是在轻松地开玩笑。',vocab:[{word:'unbelieving',level:6,meaning:'不相信的；难以置信的'},{word:'light-hearted',level:6,meaning:'轻松愉快的'}],director:d('demonstrate','🎭 示范语气',.86,1.04,410)},
  {id:17,en:'Look for the humor.',zh:'去寻找其中的幽默。',vocab:[],director:d('focus','🔎 短句强调',.8,.96,420)},
  {id:18,en:'It often comes from the unexpected.',zh:'幽默往往就诞生于出人意料之处。',vocab:[],director:d('insight','✨ 关键洞见',.82,1.06,500)},
  {id:19,en:'A twist on a familiar quote “If at first you don’t succeed, give up” or a play on words or on a situation.',zh:'你可以把一句熟悉的名言稍加扭转，比如把“如果第一次没有成功，就放弃吧”拿来开玩笑；也可以利用双关语，或者利用情境本身制造幽默。',vocab:[{word:'twist',level:6,meaning:'转折；巧妙改动'}],director:d('playful','😄 故意反转',.88,1.08,440)},
  {id:20,en:'Search for exaggeration and understatements.',zh:'去寻找那些可以夸张或刻意轻描淡写的地方。',vocab:[{word:'exaggeration',level:6,meaning:'夸张'},{word:'understatements',level:7,meaning:'轻描淡写；低调陈述'}],director:d('clear','🧩 技巧提示',.89,1,330)},
  {id:21,en:'Look at your talk and pick out a few words or sentences which you can turn about and inject with humor.',zh:'重新审视自己的讲话，挑出几个词或几句话，换一种说法，为它们注入幽默。',vocab:[{word:'inject',level:6,meaning:'注入'}],director:d('finish','✅ 平稳收尾',.9,.98,0)}
];
