package com.ttit.myapp.fragment;

import android.view.View;
import android.widget.ImageView;

import com.ttit.myapp.R;
import com.ttit.myapp.activity.MyCollectActivity;

import skin.support.SkinCompatManager;


public class MyFragment extends BaseFragment {

    private ImageView imgHeader;

    private final View.OnClickListener clickListener = new View.OnClickListener() {
        @Override
        public void onClick(View view) {
            int id = view.getId();
            if (id == R.id.img_header) {
                // 头像点击，暂无逻辑
            } else if (id == R.id.rl_collect) {
                navigateTo(MyCollectActivity.class);
            } else if (id == R.id.rl_skin) {
                String skin = findByKey("skin");
                if (skin.equals("night")) {
                    // 恢复应用默认皮肤
                    SkinCompatManager.getInstance().restoreDefaultTheme();
                    insertVal("skin", "default");
                } else {
                    SkinCompatManager.getInstance().loadSkin("night", SkinCompatManager.SKIN_LOADER_STRATEGY_BUILD_IN); // 后缀加载
                    insertVal("skin", "night");
                }
            }
        }
    };

    public MyFragment() {
    }

    public static MyFragment newInstance() {
        MyFragment fragment = new MyFragment();
        return fragment;
    }

    @Override
    protected int initLayout() {
        return R.layout.fragment_my;
    }

    @Override
    protected void initView() {
        imgHeader = mRootView.findViewById(R.id.img_header);
        mRootView.findViewById(R.id.img_header).setOnClickListener(clickListener);
        mRootView.findViewById(R.id.rl_collect).setOnClickListener(clickListener);
        mRootView.findViewById(R.id.rl_skin).setOnClickListener(clickListener);
    }

    @Override
    protected void initData() {

    }
}
